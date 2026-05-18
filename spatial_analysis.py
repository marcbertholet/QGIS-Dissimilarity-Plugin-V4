import math
import numpy as np
from scipy import spatial, stats
from collections import defaultdict


class SpatialAnalyzer:
    """Compute spatial autocorrelation and clustering indices"""
    
    def __init__(self, layer, feats, contributions):
        self.layer = layer
        self.feats = feats
        self.contributions = contributions  # List of (feat, contrib, a, total)
        self.n = len(feats)
        self.values = np.array([c[1] for c in contributions])  # contrib values
        self.coords = np.array([[
            f.geometry().centroid().x(),
            f.geometry().centroid().y()
        ] for f in feats])
    
    def _build_weight_matrix(self, weight_type="queen"):
        """Build spatial weight matrix"""
        if weight_type == "queen":
            return self._queen_weights()
        elif weight_type == "rook":
            return self._rook_weights()
        elif weight_type == "inverse_distance":
            return self._inverse_distance_weights()
        elif weight_type == "knn":
            return self._knn_weights(k=5)
        else:
            return self._queen_weights()
    
    def _queen_weights(self):
        """Queen contiguity (shares edge or node)"""
        W = defaultdict(dict)
        
        for i, feat_i in enumerate(self.feats):
            geom_i = feat_i.geometry()
            
            for j, feat_j in enumerate(self.feats):
                if i == j:
                    continue
                geom_j = feat_j.geometry()
                
                if geom_i.touches(geom_j) or geom_i.intersects(geom_j):
                    W[i][j] = 1.0
        
        # Row-standardize
        for i in W:
            if len(W[i]) > 0:
                total = sum(W[i].values())
                for j in W[i]:
                    W[i][j] /= total
        
        return W
    
    def _rook_weights(self):
        """Rook contiguity (shares edge only)"""
        W = defaultdict(dict)
        
        for i, feat_i in enumerate(self.feats):
            geom_i = feat_i.geometry()
            
            for j, feat_j in enumerate(self.feats):
                if i == j:
                    continue
                geom_j = feat_j.geometry()
                
                if geom_i.touches(geom_j):
                    W[i][j] = 1.0
        
        # Row-standardize
        for i in W:
            if len(W[i]) > 0:
                total = sum(W[i].values())
                for j in W[i]:
                    W[i][j] /= total
        
        return W
    
    def _inverse_distance_weights(self):
        """Inverse distance weights (1/d²)"""
        W = defaultdict(dict)
        
        for i in range(self.n):
            for j in range(self.n):
                if i == j:
                    continue
                dist = np.linalg.norm(self.coords[i] - self.coords[j])
                if dist > 0:
                    W[i][j] = 1.0 / (dist ** 2)
        
        # Row-standardize
        for i in W:
            if len(W[i]) > 0:
                total = sum(W[i].values())
                for j in W[i]:
                    W[i][j] /= total
        
        return W
    
    def _knn_weights(self, k=5):
        """K-Nearest Neighbors weights"""
        W = defaultdict(dict)
        
        tree = spatial.cKDTree(self.coords)
        _, indices = tree.query(self.coords, k=k+1)
        
        for i in range(self.n):
            for j in indices[i][1:]:  # Skip self
                W[i][j] = 1.0 / k
        
        return W
    
    def compute_moran(self, weight_type="queen"):
        """Moran's I - Global spatial autocorrelation"""
        W = self._build_weight_matrix(weight_type)
        
        # Standardize values
        mean_val = np.mean(self.values)
        deviations = self.values - mean_val
        
        # Compute Moran's I
        numerator = 0.0
        denominator = np.sum(deviations ** 2)
        
        for i in range(self.n):
            for j in W.get(i, {}):
                numerator += deviations[i] * deviations[j] * W[i][j]
        
        # Count neighbors
        S0 = sum(sum(w.values()) for w in W.values())
        
        if S0 == 0 or denominator == 0:
            return {"I": 0, "z_score": 0, "p_value": 1.0}
        
        I = (self.n / S0) * (numerator / denominator)
        
        # Expected value under null hypothesis
        E_I = -1.0 / (self.n - 1)
        
        # Variance (simplified)
        b2 = np.sum(deviations ** 4) / (self.n * (np.sum(deviations ** 2) / self.n) ** 2)
        
        S1 = 0.5 * sum(
            sum((W[i].get(j, 0) + W[j].get(i, 0)) ** 2 for j in range(self.n))
            for i in range(self.n)
        )
        
        var_I = ((self.n * S1 - b2 * S0) / ((S0 ** 2) * (self.n - 1))) - (E_I ** 2)
        
        if var_I <= 0:
            var_I = 1e-10
        
        z_score = (I - E_I) / np.sqrt(var_I)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        return {
            "I": I,
            "z_score": z_score,
            "p_value": p_value,
            "E_I": E_I,
            "var_I": var_I
        }
    
    def compute_geary(self, weight_type="queen"):
        """Geary's C - Alternative autocorrelation measure"""
        W = self._build_weight_matrix(weight_type)
        
        mean_val = np.mean(self.values)
        deviations = self.values - mean_val
        
        # Compute Geary's C
        numerator = 0.0
        
        for i in range(self.n):
            for j in W.get(i, {}):
                numerator += (deviations[i] - deviations[j]) ** 2 * W[i][j]
        
        denominator = 2.0 * np.sum(deviations ** 2)
        S0 = sum(sum(w.values()) for w in W.values())
        
        if denominator == 0:
            return {"C": 0, "z_score": 0, "p_value": 1.0}
        
        C = (self.n - 1) / (2 * S0) * (numerator / denominator)
        
        # Expected value
        E_C = 1.0
        
        # Variance (simplified)
        var_C = ((2 * (self.n - 1) * S0 - self.n + 3) / (4 * (S0 ** 2))) - ((self.n - 1) ** 2 / (4 * (S0 ** 2)))
        
        if var_C <= 0:
            var_C = 1e-10
        
        z_score = (C - E_C) / np.sqrt(var_C)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        return {
            "C": C,
            "z_score": z_score,
            "p_value": p_value
        }
    
    def compute_lisa(self, weight_type="queen"):
        """Local Indicators of Spatial Association (LISA)"""
        W = self._build_weight_matrix(weight_type)
        
        mean_val = np.mean(self.values)
        deviations = self.values - mean_val
        variance = np.var(self.values)
        
        if variance == 0:
            variance = 1e-10
        
        lisa_values = []
        lisa_p_values = []
        quadrants = {}
        
        for i in range(self.n):
            weighted_sum = 0.0
            for j in W.get(i, {}):
                weighted_sum += (deviations[j] / variance) * W[i][j]
            
            lisa_i = deviations[i] * weighted_sum
            lisa_values.append(lisa_i)
            
            # Determine quadrant
            quad_i = "H" if deviations[i] > 0 else "L"
            quad_j = "H" if weighted_sum > 0 else "L"
            quadrants[i] = quad_i + quad_j
        
        lisa_values = np.array(lisa_values)
        
        # Count quadrants
        counts = defaultdict(int)
        for i, quad in quadrants.items():
            counts[quad] += 1
        counts["NS"] = self.n - sum(counts.values())
        
        return {
            "values": lisa_values,
            "quadrants": quadrants,
            "counts": dict(counts)
        }
    
    def compute_getis_ord(self, weight_type="queen"):
        """Getis-Ord Gi* - Local hotspot analysis"""
        W = self._build_weight_matrix(weight_type)
        
        mean_val = np.mean(self.values)
        std_val = np.std(self.values)
        
        if std_val == 0:
            std_val = 1e-10
        
        z_scores = []
        hotspots = 0
        coldspots = 0
        
        for i in range(self.n):
            # Include self in calculation
            weighted_sum = self.values[i]
            weight_sum = 1.0
            
            for j in W.get(i, {}):
                weighted_sum += self.values[j] * W[i][j]
                weight_sum += W[i][j]
            
            mean_weighted = (mean_val * weight_sum)
            
            # Calculate Z-score
            numerator = weighted_sum - mean_weighted
            denominator = std_val * np.sqrt(weight_sum)
            
            if denominator > 0:
                z = numerator / denominator
                z_scores.append(z)
                
                if z > 1.96:  # p < 0.05
                    hotspots += 1
                elif z < -1.96:
                    coldspots += 1
            else:
                z_scores.append(0)
        
        return {
            "z_scores": z_scores,
            "hotspots": hotspots,
            "coldspots": coldspots
        }
    
    def compute_ripleys_k(self, r_max=None):
        """Ripley's K - Clustering vs regularity analysis"""
        if r_max is None:
            r_max = np.max(spatial.distance.pdist(self.coords)) / 2
        
        r_values = np.linspace(0.01 * r_max, r_max, 20)
        k_values = []
        
        # Compute pairwise distances
        distances = spatial.distance.pdist(self.coords)
        
        for r in r_values:
            count = np.sum(distances <= r)
            k = count * (np.sum(np.ones((self.n, self.n))) / (self.n ** 2)) / (np.pi * r ** 2)
            k_values.append(k)
        
        return {
            "r_values": r_values.tolist(),
            "k_values": k_values
        }
    
    def compute_distance_decay(self):
        """Distance decay - Correlation between distance and dissimilarity"""
        # Compute pairwise distances
        distances = spatial.distance.pdist(self.coords)
        
        # Compute pairwise value differences
        n = self.n
        diffs = []
        
        for i in range(n):
            for j in range(i + 1, n):
                diffs.append(abs(self.values[i] - self.values[j]))
        
        diffs = np.array(diffs)
        
        # Correlation
        correlation = np.corrcoef(distances, diffs)[0, 1]
        
        # Linear regression
        from numpy.polynomial import polynomial as P
        coeffs = P.polyfit(distances, diffs, 1)
        
        return {
            "correlation": correlation,
            "slope": coeffs[1],
            "intercept": coeffs[0]
        }
