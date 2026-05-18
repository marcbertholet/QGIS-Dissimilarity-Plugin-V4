    def _create_output_layer(self, results):
        """Create a new layer with results and styling"""
        geom_type = self.layer.geometryType()
        
        if geom_type == 0:
            geom_str = "Point"
        elif geom_type == 1:
            geom_str = "LineString"
        elif geom_type == 2:
            geom_str = "Polygon"
        else:
            QMessageBox.warning(self, "Error", "Unsupported geometry type")
            return
        
        crs = self.layer.crs().authid()
        
        # Create memory layer
        out = QgsVectorLayer(f"{geom_str}?crs={crs}", "Dissimilarity_Results_V4", "memory")
        pr = out.dataProvider()
        
        # Add all original fields
        pr.addAttributes(self.layer.fields())
        
        # Add new result fields
        pr.addAttributes([
            QgsField("contrib", QVariant.Double),
            QgsField("share_A", QVariant.Double),
            QgsField("share_total", QVariant.Double)
        ])
        
        if "lisa" in results:
            pr.addAttributes([QgsField("lisa_quad", QVariant.String)])
        
        if "getis" in results:
            pr.addAttributes([QgsField("getis_z_score", QVariant.Double)])
        
        out.updateFields()
        
        # Add features with geometries
        new_feats = []
        totalA = results["totalA"]
        totalB = results["totalB"]
        
        # Use the original features from the layer
        for i, original_feat in enumerate(results["feats"]):
            nf = QgsFeature(out.fields())
            
            # Copy geometry from original feature
            nf.setGeometry(original_feat.geometry())
            
            # Get the contribution data for this feature
            if i < len(results["contributions"]):
                f, c, a, total = results["contributions"][i]
                
                # Copy all original attributes
                nf.setAttributes(original_feat.attributes())
                
                # Calculate additional values
                share_A = a / total if total > 0 else 0
                share_total = total / (totalA + totalB) if (totalA + totalB) > 0 else 0
                
                # Add new field values
                new_attrs = list(nf.attributes()) + [c, share_A, share_total]
                
                if "lisa" in results:
                    lisa_quad = results["lisa"]["quadrants"].get(i, "NS")
                    new_attrs.append(lisa_quad)
                
                if "getis" in results:
                    getis_z = results["getis"]["z_scores"][i] if i < len(results["getis"]["z_scores"]) else 0
                    new_attrs.append(getis_z)
                
                nf.setAttributes(new_attrs)
                new_feats.append(nf)
        
        # Add all features at once
        pr.addFeatures(new_feats)
        out.updateExtents()
        
        # Apply styling based on available data
        if "lisa" in results:
            self._apply_lisa_styling(out)
        elif "getis" in results:
            self._apply_getis_styling(out)
        else:
            self._apply_styling(out, "contrib")
        
        QgsProject.instance().addMapLayer(out)
        self.iface.mapCanvas().zoomToFullExtent()
