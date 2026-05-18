import csv
import json
from datetime import datetime


class ExportHandler:
    """Handle exports to various formats"""
    
    def __init__(self, results, layer):
        self.results = results
        self.layer = layer
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def export_csv(self, filepath):
        """Export to CSV format"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            header = ['feature_id', 'contribution', 'share_A', 'share_total']
            if 'lisa' in self.results:
                header.append('lisa_quadrant')
            writer.writerow(header)
            
            # Data
            totalA = self.results['totalA']
            totalB = self.results['totalB']
            
            for i, (feat, contrib, a, total) in enumerate(self.results['contributions']):
                share_A = a / total if total > 0 else 0
                share_total = total / (totalA + totalB) if (totalA + totalB) > 0 else 0
                
                row = [i, contrib, share_A, share_total]
                
                if 'lisa' in self.results:
                    quad = self.results['lisa']['quadrants'].get(i, 'NS')
                    row.append(quad)
                
                writer.writerow(row)
    
    def export_json(self, filepath):
        """Export to JSON format"""
        output = {
            "timestamp": self.timestamp,
            "layer_name": self.layer.name(),
            "dissimilarity_index": self.results['D'],
            "dissimilarity_percent": self.results['D'] * 100,
            "feature_count": len(self.results['contributions']),
            "indices": {}
        }
        
        # Add Moran's I
        if 'moran' in self.results:
            moran = self.results['moran']
            output["indices"]["morans_i"] = {
                "I": moran['I'],
                "z_score": moran['z_score'],
                "p_value": moran['p_value'],
                "interpretation": "Significant clustering" if moran['p_value'] < 0.05 and moran['I'] > 0 else "No significant autocorrelation"
            }
        
        # Add Geary's C
        if 'geary' in self.results:
            geary = self.results['geary']
            output["indices"]["gearys_c"] = {
                "C": geary['C'],
                "z_score": geary['z_score'],
                "p_value": geary['p_value']
            }
        
        # Add LISA
        if 'lisa' in self.results:
            lisa = self.results['lisa']
            output["indices"]["lisa"] = {
                "hot_spots": lisa['counts'].get('HH', 0),
                "cold_spots": lisa['counts'].get('LL', 0),
                "high_low_outliers": lisa['counts'].get('HL', 0),
                "low_high_outliers": lisa['counts'].get('LH', 0),
                "not_significant": lisa['counts'].get('NS', 0)
            }
        
        # Add Getis-Ord
        if 'getis' in self.results:
            getis = self.results['getis']
            output["indices"]["getis_ord"] = {
                "hotspots": getis['hotspots'],
                "coldspots": getis['coldspots']
            }
        
        # Add statistics
        if 'stats' in self.results:
            stats = self.results['stats']
            output["indices"]["statistics"] = {
                "gini_coefficient": stats.get('gini', 0),
                "hhi": stats.get('hhi', 0),
                "shannon_entropy": stats.get('shannon', 0),
                "simpson_index": stats.get('simpson', 0),
                "mean_contribution": stats.get('mean_contrib', 0),
                "std_contribution": stats.get('std_contrib', 0),
                "median_contribution": stats.get('median_contrib', 0),
                "cv_contribution": stats.get('cv_contrib', 0)
            }
        
        # Add feature-level data
        features_data = []
        totalA = self.results['totalA']
        totalB = self.results['totalB']
        
        for i, (feat, contrib, a, total) in enumerate(self.results['contributions']):
            share_A = a / total if total > 0 else 0
            share_total = total / (totalA + totalB) if (totalA + totalB) > 0 else 0
            
            feature_data = {
                "feature_id": i,
                "contribution": contrib,
                "share_A": share_A,
                "share_total": share_total
            }
            
            if 'lisa' in self.results:
                feature_data['lisa_quadrant'] = self.results['lisa']['quadrants'].get(i, 'NS')
            
            features_data.append(feature_data)
        
        output["features"] = features_data
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
    
    def export_geojson(self, filepath):
        """Export to GeoJSON format"""
        features = []
        totalA = self.results['totalA']
        totalB = self.results['totalB']
        
        for i, feat in enumerate(self.results['feats']):
            contrib_data = self.results['contributions'][i]
            contrib = contrib_data[1]
            a = contrib_data[2]
            total = contrib_data[3]
            
            share_A = a / total if total > 0 else 0
            share_total = total / (totalA + totalB) if (totalA + totalB) > 0 else 0
            
            geom = feat.geometry()
            
            # Convert geometry to GeoJSON
            if geom.isMultipart():
                geom_type = "Multi" + self._get_geom_type(geom.type())
                coords = self._extract_multi_coords(geom)
            else:
                geom_type = self._get_geom_type(geom.type())
                coords = self._extract_coords(geom)
            
            properties = {
                "contribution": contrib,
                "share_A": share_A,
                "share_total": share_total
            }
            
            if 'lisa' in self.results:
                properties['lisa_quadrant'] = self.results['lisa']['quadrants'].get(i, 'NS')
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": geom_type,
                    "coordinates": coords
                },
                "properties": properties
            }
            
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "timestamp": self.timestamp,
            "layer_name": self.layer.name(),
            "dissimilarity_index": self.results['D'],
            "features": features
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    def _get_geom_type(self, qgis_type):
        """Convert QGIS geometry type to GeoJSON type"""
        if qgis_type == 0:
            return "Point"
        elif qgis_type == 1:
            return "LineString"
        elif qgis_type == 2:
            return "Polygon"
        else:
            return "Unknown"
    
    def _extract_coords(self, geom):
        """Extract coordinates from QGIS geometry"""
        geom_type = geom.type()
        
        if geom_type == 0:  # Point
            pt = geom.asPoint()
            return [pt.x(), pt.y()]
        elif geom_type == 1:  # LineString
            pts = geom.asPolyline()
            return [[pt.x(), pt.y()] for pt in pts]
        elif geom_type == 2:  # Polygon
            rings = geom.asPolygon()
            return [[[pt.x(), pt.y()] for pt in ring] for ring in rings]
        else:
            return []
    
    def _extract_multi_coords(self, geom):
        """Extract coordinates from multipart geometry"""
        geom_type = geom.type()
        
        if geom_type == 0:  # MultiPoint
            pts = geom.asMultiPoint()
            return [[pt.x(), pt.y()] for pt in pts]
        elif geom_type == 1:  # MultiLineString
            lines = geom.asMultiPolyline()
            return [[[pt.x(), pt.y()] for pt in line] for line in lines]
        elif geom_type == 2:  # MultiPolygon
            polygons = geom.asMultiPolygon()
            result = []
            for polygon in polygons:
                result.append([[[pt.x(), pt.y()] for pt in ring] for ring in polygon])
            return result
        else:
            return []
