# Dissimilarity Index PRO V4

**Advanced Spatial Dissimilarity Analysis Plugin for QGIS**

## Features

### 🎯 Core Functionality
- **Dissimilarity Index (D)** - Measure of segregation/dissimilarity between two groups
- Multi-field analysis with flexible configuration
- Automatic layer generation with results
- Export in multiple formats (CSV, JSON, GeoJSON)

### 📊 Spatial Autocorrelation Indices

#### Global Measures
- **Moran's I** - Global spatial autocorrelation (clustering detection)
  - Ranges from -1 (dispersed) to +1 (clustered)
  - Includes Z-score and p-value for significance testing
  - Interpretation: Positive values indicate clustering of similar values

- **Geary's C** - Alternative autocorrelation measure
  - More sensitive to local differences
  - Ranges from 0 (strong clustering) to 2+ (dispersion)
  - Useful for detecting micro-scale patterns

#### Local Measures
- **LISA (Local Moran's I)**
  - Identifies hot-spots (HH), cold-spots (LL), and outliers
  - Quadrants: HH, LL, HL, LH, NS (not significant)
  - Shows where clustering is concentrated

- **Getis-Ord Gi***
  - Identifies statistically significant hotspots and coldspots
  - Uses Z-scores (±1.96 threshold for p<0.05)
  - Better for intensity analysis

#### Pattern Analysis
- **Ripley's K Function** - Clustering vs regularity
- **Distance Decay** - Correlation between spatial distance and dissimilarity

### 📈 Statistical Indices

- **Gini Coefficient** - Income/wealth inequality measure (0-1)
- **HHI** (Herfindahl-Hirschman Index) - Concentration measure
- **Shannon Entropy** - Diversity and heterogeneity
- **Simpson Index** - Biodiversity-style diversity measure
- **Descriptive Statistics** - Mean, median, std dev, min, max of contributions
- **Coefficient of Variation** - Relative variability

### ⚙️ Weight Matrices

- **Queen Contiguity** - Shares edge or node (default)
- **Rook Contiguity** - Shares edge only
- **Inverse Distance** - Weight = 1/d² (continuous)
- **K-Nearest Neighbors** - Fixed k neighbors (default k=5)

### 🎨 Visualization

- Automatic layer generation from results
- Graduated symbol styling with Viridis colormap
- Color-coded by contribution values
- Layer added directly to QGIS map canvas

### 💾 Export Formats

- **CSV** - Tabular data with contributions and shares
- **JSON** - All indices and feature-level data
- **GeoJSON** - Spatial features with properties included

## Installation

1. Download the plugin zip file
2. Extract to: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - On Windows: `C:\Users\[username]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
3. Restart QGIS
4. Go to Plugins → Manage Plugins → search "Dissimilarity" → check to enable
5. Icon appears in toolbar

## Quick Start

### Basic Analysis

1. Load a polygon layer in QGIS (e.g., census tracts, neighborhoods)
2. Open the plugin: **Plugins → Dissimilarity Index PRO V4**
3. **Configuration Tab:**
   - Select "Group A" field (e.g., population of group X)
   - Select "Total Population" field
   - Choose weight matrix (default: Queen contiguity)
4. **Spatial Analysis Tab:**
   - Check desired indices (Moran's I, LISA, etc.)
5. **Statistics Tab:**
   - Check "Compute Statistical Indices" if desired
6. Click **"Compute Analysis"**
7. View results in **"Results" tab**
8. Export via **"Export Results"** button

### Interpretation Guide

#### Dissimilarity Index
```
D = 0.00 - 0.30  → Low segregation
D = 0.30 - 0.60  → Moderate segregation
D = 0.60 - 1.00  → High segregation
```

#### Moran's I
```
I > 0, p < 0.05  → Significant spatial clustering ✓
I < 0, p < 0.05  → Significant spatial dispersion
I ≈ 0, p > 0.05  → Random spatial pattern
```

#### LISA Quadrants
```
HH = High-High   → Hot spots (areas of high values surrounded by high)
LL = Low-Low     → Cold spots (areas of low values surrounded by low)
HL = High-Low    → Outlier (high area surrounded by low)
LH = Low-High    → Outlier (low area surrounded by high)
NS = Not Sig     → No significant local autocorrelation
```

#### Statistical Indices
```
Gini:     0 = Perfect equality, 1 = Perfect inequality
HHI:      0 = Perfect competition, 10000 = Monopoly
Shannon:  Higher = More diverse
Simpson:  0 = Low diversity, 1 = High diversity
```

## Examples

### Example 1: Racial Segregation
**Data:** Census tracts with populations by race
- Group A = Population of Race X
- Total = Total Population
- Result: D index + LISA hotspots show segregated neighborhoods

### Example 2: Income Inequality
**Data:** Neighborhoods with income data
- Group A = High-income population
- Total = Total population
- Result: Gini coefficient + spatial clustering analysis

### Example 3: Disease Distribution
**Data:** Administrative units with cases
- Group A = Confirmed cases
- Total = Total population at risk
- Result: Getis-Ord identifies disease hotspots

## Technical Details

### Moran's I Calculation
```
I = (n/S0) × Σᵢ Σⱼ wᵢⱼ (xᵢ - x̄)(xⱼ - x̄) / Σᵢ (xᵢ - x̄)²

Where:
- n = number of features
- S0 = sum of all weights
- wᵢⱼ = weight between features i and j
- x = values (contributions)
```

### Getis-Ord Gi* Calculation
```
Gi* = [Σⱼ wᵢⱼ xⱼ - W̄ Σₖ xₖ] / √{[S(Σⱼ wᵢⱼ²) - (Σⱼ wᵢⱼ)²] / (n-1)} × √[Σₖ xₖ² / n - (Σₖ xₖ / n)²]
```

## Requirements

- QGIS >= 3.0
- Python >= 3.6
- NumPy
- SciPy
- PyQt5

## Troubleshooting

### "No active layer" error
- Make sure you have selected a layer in the Layers panel
- The layer must be a vector layer (polygon/line/point)

### "Group A is empty" error
- Check your data: all values in the Group A field are 0 or NULL
- Select a different field

### Results look wrong
- Verify your weight matrix choice matches your data type
- For polygon data, "Queen" is usually best
- For point data, use "K-Nearest Neighbors"

### Slow computation
- This is normal for large datasets (1000+ features)
- The plugin uses background threading to avoid freezing
- Results will display when computation completes

## References

1. Moran, P. A. (1950). Notes on continuous stochastic phenomena. Biometrika, 37(1/2), 17-23.
2. Geary, R. C. (1954). The contiguity ratio and statistical mapping. The Incorporated Statistician, 5(3), 115-145.
3. Anselin, L. (1995). Local Indicators of Spatial Association—LISA. Geographical Analysis, 27(2), 93-115.
4. Getis, A., & Ord, J. K. (1992). The analysis of spatial association by use of distance statistics. Geographical Analysis, 24(3), 189-206.
5. Ripley, B. D. (1976). The second-order analysis of stationary point processes. Journal of Applied Probability, 13(2), 255-266.
6. Gini, C. (1912). Variabilità e mutabilità. Bologna: C. Cuppini.

## License

MIT License - Feel free to use and modify

## Author

Marc Bertholet

## Support

For issues and feature requests, visit:
https://github.com/marcbertholet/QGIS-Dissimilarity-Plugin-V4/issues
