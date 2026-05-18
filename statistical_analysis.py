import numpy as np
from scipy import stats


class StatisticalAnalyzer:
    """Compute statistical indices for dissimilarity and segregation"""
    
    def __init__(self, vals, contributions, totalA, totalB):
        """
        vals: List of (feat, a, b, total)
        contributions: List of (feat, contrib, a, total)
        """
        self.vals = vals
        self.contributions = contributions
        self.totalA = totalA
        self.totalB = totalB
        self.contrib_values = np.array([c[1] for c in contributions])
    
    def compute_all(self):
        """Compute all statistical indices"""
        return {
            "gini": self.compute_gini(),
            "hhi": self.compute_hhi(),
            "shannon": self.compute_shannon_entropy(),
            "simpson": self.compute_simpson_index(),
            "mean_contrib": self.compute_mean_contrib(),
            "std_contrib": self.compute_std_contrib(),
            "median_contrib": self.compute_median_contrib(),
            "max_contrib": self.compute_max_contrib(),
            "min_contrib": self.compute_min_contrib(),
            "cv_contrib": self.compute_cv_contrib(),
        }
    
    def compute_gini(self):
        """Gini Coefficient - Inequality measure"""
        if len(self.contrib_values) == 0:
            return 0.0
        
        sorted_contrib = np.sort(self.contrib_values)
        n = len(sorted_contrib)
        cumsum = np.cumsum(sorted_contrib)
        
        gini = (2 * np.sum((n + 1 - np.arange(1, n + 1)) * sorted_contrib)) / (n * np.sum(sorted_contrib)) - (n + 1) / n
        
        return max(0, min(1, gini))
    
    def compute_hhi(self):
        """Herfindahl-Hirschman Index - Concentration measure"""
        if len(self.contrib_values) == 0:
            return 0.0
        
        # Normalize contributions to sum to 1
        total = np.sum(self.contrib_values)
        if total == 0:
            return 0.0
        
        shares = self.contrib_values / total
        hhi = np.sum(shares ** 2)
        
        return hhi
    
    def compute_shannon_entropy(self):
        """Shannon Entropy - Diversity measure"""
        if len(self.contrib_values) == 0:
            return 0.0
        
        # Normalize contributions
        total = np.sum(self.contrib_values)
        if total == 0:
            return 0.0
        
        shares = self.contrib_values / total
        shares = shares[shares > 0]  # Remove zeros
        
        entropy = -np.sum(shares * np.log(shares))
        
        return entropy
    
    def compute_simpson_index(self):
        """Simpson Diversity Index"""
        if len(self.contrib_values) == 0:
            return 0.0
        
        # Normalize contributions
        total = np.sum(self.contrib_values)
        if total == 0:
            return 0.0
        
        shares = self.contrib_values / total
        simpson = 1.0 - np.sum(shares ** 2)
        
        return simpson
    
    def compute_mean_contrib(self):
        """Mean contribution"""
        if len(self.contrib_values) == 0:
            return 0.0
        return np.mean(self.contrib_values)
    
    def compute_std_contrib(self):
        """Standard deviation of contributions"""
        if len(self.contrib_values) == 0:
            return 0.0
        return np.std(self.contrib_values)
    
    def compute_median_contrib(self):
        """Median contribution"""
        if len(self.contrib_values) == 0:
            return 0.0
        return np.median(self.contrib_values)
    
    def compute_max_contrib(self):
        """Maximum contribution"""
        if len(self.contrib_values) == 0:
            return 0.0
        return np.max(self.contrib_values)
    
    def compute_min_contrib(self):
        """Minimum contribution"""
        if len(self.contrib_values) == 0:
            return 0.0
        return np.min(self.contrib_values)
    
    def compute_cv_contrib(self):
        """Coefficient of variation (std/mean)"""
        mean = self.compute_mean_contrib()
        std = self.compute_std_contrib()
        
        if mean == 0:
            return 0.0
        
        return std / mean
    
    def compute_atkinson_index(self, epsilon=0.5):
        """Atkinson Index - Inequality measure with inequality aversion parameter"""
        if len(self.contrib_values) == 0:
            return 0.0
        
        total = np.sum(self.contrib_values)
        if total == 0:
            return 0.0
        
        shares = self.contrib_values / total
        shares = shares[shares > 0]
        
        if epsilon == 1:
            atkinson = 1 - np.exp(np.mean(np.log(shares)))
        else:
            atkinson = 1 - (np.mean(shares ** (1 - epsilon))) ** (1 / (1 - epsilon))
        
        return max(0, min(1, atkinson))
    
    def compute_theil_index(self):
        """Theil Index - Entropy-based inequality measure"""
        if len(self.contrib_values) == 0:
            return 0.0
        
        total = np.sum(self.contrib_values)
        if total == 0:
            return 0.0
        
        shares = self.contrib_values / total
        shares = shares[shares > 0]
        
        theil = np.sum(shares * np.log(shares / np.mean(shares)))
        
        return max(0, theil)
