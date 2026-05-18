from qgis.PyQt.QtWidgets import (
    QAction, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTabWidget, QWidget,
    QCheckBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QTextEdit, QFileDialog
)
from qgis.PyQt.QtCore import QThread, pyqtSignal, Qt
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsField, QgsProject,
    QgsSymbol, QgsRendererRange, QgsGraduatedSymbolRenderer
)
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
import os
import csv
import json
from .spatial_analysis import SpatialAnalyzer
from .statistical_analysis import StatisticalAnalyzer
from .export_handler import ExportHandler


class DissimilarityPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        self.action = QAction("Dissimilarity Index PRO V4", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        layer = self.iface.activeLayer()
        if not layer or not layer.isValid():
            QMessageBox.warning(None, "Error", "No active layer selected")
            return

        dlg = MainDialog(layer, self.iface)
        dlg.exec_()


class ComputeWorker(QThread):
    """Worker thread for heavy computations"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, layer, config):
        super().__init__()
        self.layer = layer
        self.config = config

    def run(self):
        try:
            self.progress.emit("Reading layer data...")
            feats = list(self.layer.getFeatures())
            
            # Extract values
            fieldA = self.config["fieldA"]
            fieldTotal = self.config["fieldTotal"]
            
            totalA, totalB, vals = self._extract_values(feats, fieldA, fieldTotal)
            
            if totalA == 0:
                self.error.emit("Group A is empty")
                return
            if totalB == 0:
                self.error.emit("Population B is empty")
                return

            # Calculate dissimilarity
            self.progress.emit("Computing dissimilarity index...")
            D, contributions = self._compute_dissimilarity(vals, totalA, totalB)
            
            results = {
                "D": D,
                "contributions": contributions,
                "totalA": totalA,
                "totalB": totalB,
                "vals": vals,
                "feats": feats
            }
            
            # Spatial analysis
            if self.config.get("compute_moran") or self.config.get("compute_geary") or self.config.get("compute_lisa"):
                self.progress.emit("Computing spatial indices...")
                spatial = SpatialAnalyzer(self.layer, feats, contributions)
                
                if self.config.get("compute_moran"):
                    results["moran"] = spatial.compute_moran(self.config.get("weight_type", "queen"))
                if self.config.get("compute_geary"):
                    results["geary"] = spatial.compute_geary(self.config.get("weight_type", "queen"))
                if self.config.get("compute_lisa"):
                    results["lisa"] = spatial.compute_lisa(self.config.get("weight_type", "queen"))
                if self.config.get("compute_getis"):
                    results["getis"] = spatial.compute_getis_ord(self.config.get("weight_type", "queen"))
            
            # Statistical analysis
            if self.config.get("compute_stats"):
                self.progress.emit("Computing statistical indices...")
                stats = StatisticalAnalyzer(vals, contributions, totalA, totalB)
                results["stats"] = stats.compute_all()
            
            self.progress.emit("Done!")
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

    def _extract_values(self, feats, fieldA, fieldTotal):
        totalA, totalB = 0.0, 0.0
        vals = []
        for f in feats:
            a = self._to_float(f[fieldA])
            total = self._to_float(f[fieldTotal])
            b = max(total - a, 0.0)
            totalA += a
            totalB += b
            vals.append((f, a, b, total))
        return totalA, totalB, vals

    def _compute_dissimilarity(self, vals, totalA, totalB):
        D = 0.0
        contributions = []
        for f, a, b, total in vals:
            share_A = a / totalA
            share_B = b / totalB
            contrib = 0.5 * abs(share_A - share_B)
            contributions.append((f, contrib, a, total))
            D += contrib
        return D, contributions

    @staticmethod
    def _to_float(value):
        try:
            if value is None:
                return 0.0
            return float(value)
        except:
            try:
                return float(str(value))
            except:
                return 0.0


class MainDialog(QDialog):
    def __init__(self, layer, iface):
        super().__init__()
        self.layer = layer
        self.iface = iface
        self.results = None
        self.worker = None
        
        self.setWindowTitle("Dissimilarity Index PRO V4")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        
        # Tabbed interface
        tabs = QTabWidget()
        
        # Tab 1: Configuration
        config_widget = self._create_config_tab()
        tabs.addTab(config_widget, "Configuration")
        
        # Tab 2: Spatial Analysis
        spatial_widget = self._create_spatial_tab()
        tabs.addTab(spatial_widget, "Spatial Analysis")
        
        # Tab 3: Statistics
        stats_widget = self._create_stats_tab()
        tabs.addTab(stats_widget, "Statistics")
        
        # Tab 4: Results
        results_widget = self._create_results_tab()
        tabs.addTab(results_widget, "Results")
        
        layout.addWidget(tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QLabel("Ready")
        layout.addWidget(self.status_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_compute = QPushButton("Compute Analysis")
        btn_compute.clicked.connect(self.compute)
        btn_layout.addWidget(btn_compute)
        
        btn_export = QPushButton("Export Results")
        btn_export.clicked.connect(self.export_results)
        btn_layout.addWidget(btn_export)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _create_config_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Group Field (A):"))
        self.combo_a = QComboBox()
        for f in self.layer.fields():
            if f.isNumeric():
                self.combo_a.addItem(f.name())
        layout.addWidget(self.combo_a)
        
        layout.addWidget(QLabel("Total Population Field:"))
        self.combo_total = QComboBox()
        for f in self.layer.fields():
            if f.isNumeric():
                self.combo_total.addItem(f.name())
        layout.addWidget(self.combo_total)
        
        layout.addWidget(QLabel("Weight Matrix Type:"))
        self.combo_weight = QComboBox()
        self.combo_weight.addItems(["queen", "rook", "inverse_distance", "knn"])
        layout.addWidget(self.combo_weight)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget

    def _create_spatial_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Spatial Indices:"))
        
        self.check_moran = QCheckBox("Moran's I (Global autocorrelation)")
        self.check_moran.setChecked(True)
        layout.addWidget(self.check_moran)
        
        self.check_geary = QCheckBox("Geary's C (Alternative autocorrelation)")
        layout.addWidget(self.check_geary)
        
        self.check_lisa = QCheckBox("Local Moran's I (LISA - Hot/Cold spots)")
        self.check_lisa.setChecked(True)
        layout.addWidget(self.check_lisa)
        
        self.check_getis = QCheckBox("Getis-Ord Gi* (Hotspot intensity)")
        layout.addWidget(self.check_getis)
        
        self.check_ripley = QCheckBox("Ripley's K (Clustering pattern)")
        layout.addWidget(self.check_ripley)
        
        self.check_distance_decay = QCheckBox("Distance Decay (Correlation vs distance)")
        layout.addWidget(self.check_distance_decay)
        
        layout.addWidget(QLabel("K-Nearest Neighbors (if KNN selected):"))
        self.spin_k = QSpinBox()
        self.spin_k.setValue(5)
        self.spin_k.setMinimum(1)
        self.spin_k.setMaximum(20)
        layout.addWidget(self.spin_k)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget

    def _create_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Statistical Analysis:"))
        
        self.check_stats = QCheckBox("Compute Statistical Indices")
        self.check_stats.setChecked(True)
        layout.addWidget(self.check_stats)
        
        layout.addWidget(QLabel("Includes:"))
        layout.addWidget(QLabel("• Gini Coefficient (inequality)"))
        layout.addWidget(QLabel("• HHI (concentration)"))
        layout.addWidget(QLabel("• Shannon Entropy (diversity)"))
        layout.addWidget(QLabel("• Simpson Index (species diversity)"))
        layout.addWidget(QLabel("• Descriptive Statistics"))
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget

    def _create_results_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        widget.setLayout(layout)
        return widget

    def compute(self):
        if not self.combo_a.currentText() or not self.combo_total.currentText():
            QMessageBox.warning(self, "Error", "Please select valid fields")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        config = {
            "fieldA": self.combo_a.currentText(),
            "fieldTotal": self.combo_total.currentText(),
            "weight_type": self.combo_weight.currentText(),
            "k": self.spin_k.value(),
            "compute_moran": self.check_moran.isChecked(),
            "compute_geary": self.check_geary.isChecked(),
            "compute_lisa": self.check_lisa.isChecked(),
            "compute_getis": self.check_getis.isChecked(),
            "compute_stats": self.check_stats.isChecked(),
        }
        
        self.worker = ComputeWorker(self.layer, config)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, msg):
        self.status_text.setText(msg)

    def _on_finished(self, results):
        self.results = results
        self.progress_bar.setVisible(False)
        self._display_results(results)
        self._create_output_layer(results)
        self.status_text.setText("Analysis completed successfully!")

    def _on_error(self, error_msg):
        QMessageBox.critical(self, "Error", error_msg)
        self.progress_bar.setVisible(False)

    def _display_results(self, results):
        text = ""
        
        # Dissimilarity Index
        D = results["D"]
        percent = D * 100
        
        if percent < 30:
            interp = "Low segregation"
        elif percent < 60:
            interp = "Moderate segregation"
        else:
            interp = "High segregation"
        
        text += f"=== DISSIMILARITY INDEX ===\n"
        text += f"D Index: {D:.4f}\n"
        text += f"Percentage: {percent:.2f}%\n"
        text += f"Interpretation: {interp}\n\n"
        
        # Moran's I
        if "moran" in results:
            moran = results["moran"]
            text += f"=== MORAN'S I ===\n"
            text += f"I: {moran['I']:.4f}\n"
            text += f"Z-score: {moran['z_score']:.4f}\n"
            text += f"P-value: {moran['p_value']:.6f}\n"
            text += f"Interpretation: "
            if moran['p_value'] < 0.05:
                if moran['I'] > 0:
                    text += "Significant POSITIVE spatial autocorrelation (clustering)\n"
                else:
                    text += "Significant NEGATIVE spatial autocorrelation (dispersion)\n"
            else:
                text += "No significant spatial autocorrelation\n"
            text += "\n"
        
        # Geary's C
        if "geary" in results:
            geary = results["geary"]
            text += f"=== GEARY'S C ===\n"
            text += f"C: {geary['C']:.4f}\n"
            text += f"Z-score: {geary['z_score']:.4f}\n"
            text += f"P-value: {geary['p_value']:.6f}\n\n"
        
        # LISA
        if "lisa" in results:
            lisa = results["lisa"]
            text += f"=== LOCAL MORAN'S I (LISA) ===\n"
            text += f"Hot-spots (HH): {lisa['counts'].get('HH', 0)}\n"
            text += f"Cold-spots (LL): {lisa['counts'].get('LL', 0)}\n"
            text += f"High-Low outliers: {lisa['counts'].get('HL', 0)}\n"
            text += f"Low-High outliers: {lisa['counts'].get('LH', 0)}\n"
            text += f"Not significant: {lisa['counts'].get('NS', 0)}\n\n"
        
        # Getis-Ord
        if "getis" in results:
            getis = results["getis"]
            text += f"=== GETIS-ORD Gi* ===\n"
            text += f"Hotspots (p<0.05): {getis['hotspots']}\n"
            text += f"Coldspots (p<0.05): {getis['coldspots']}\n\n"
        
        # Statistics
        if "stats" in results:
            stats = results["stats"]
            text += f"=== STATISTICAL INDICES ===\n"
            text += f"Gini Coefficient: {stats.get('gini', 0):.4f}\n"
            text += f"HHI: {stats.get('hhi', 0):.4f}\n"
            text += f"Shannon Entropy: {stats.get('shannon', 0):.4f}\n"
            text += f"Simpson Index: {stats.get('simpson', 0):.4f}\n"
            text += f"Mean Contribution: {stats.get('mean_contrib', 0):.4f}\n"
            text += f"Std Dev Contribution: {stats.get('std_contrib', 0):.4f}\n"
        
        self.results_text.setText(text)

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
        
        pr.addAttributes(self.layer.fields())
        pr.addAttributes([
            QgsField("contrib", QVariant.Double),
            QgsField("share_A", QVariant.Double),
            QgsField("share_total", QVariant.Double)
        ])
        
        if "lisa" in results:
            pr.addAttributes([QgsField("lisa_quad", QVariant.String)])
        
        out.updateFields()
        
        # Add features
        new_feats = []
        totalA = results["totalA"]
        totalB = results["totalB"]
        
        for i, (f, c, a, total) in enumerate(results["contributions"]):
            nf = QgsFeature(out.fields())
            nf.setGeometry(f.geometry())
            
            share_A = a / total if total > 0 else 0
            share_total = total / (totalA + totalB) if (totalA + totalB) > 0 else 0
            
            attrs = f.attributes() + [c, share_A, share_total]
            
            if "lisa" in results:
                lisa_quad = results["lisa"]["quadrants"].get(i, "NS")
                attrs.append(lisa_quad)
            
            nf.setAttributes(attrs)
            new_feats.append(nf)
        
        pr.addFeatures(new_feats)
        out.updateExtents()
        
        # Apply styling
        self._apply_styling(out, "contrib")
        
        QgsProject.instance().addMapLayer(out)
        self.iface.mapCanvas().zoomToFullExtent()

    def _apply_styling(self, layer, field_name):
        """Apply graduated styling with viridis colormap"""
        provider = layer.dataProvider()
        field_index = layer.fields().indexFromName(field_name)
        
        if field_index == -1:
            return
        
        # Get min/max values
        values = []
        for feat in layer.getFeatures():
            val = feat[field_name]
            if val is not None:
                values.append(float(val))
        
        if not values:
            return
        
        min_val = min(values)
        max_val = max(values)
        
        # Viridis colors
        colors = [
            QColor(68, 1, 84),      # Dark purple
            QColor(59, 82, 139),    # Blue
            QColor(33, 145, 140),   # Cyan
            QColor(253, 231, 37)    # Yellow
        ]
        
        ranges = []
        for i in range(len(colors)):
            lower = min_val + (max_val - min_val) * i / len(colors)
            upper = min_val + (max_val - min_val) * (i + 1) / len(colors)
            
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(colors[i])
            
            rng = QgsRendererRange(lower, upper, symbol, f"{lower:.3f} - {upper:.3f}")
            ranges.append(rng)
        
        renderer = QgsGraduatedSymbolRenderer(field_name, ranges)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def export_results(self):
        if not self.results:
            QMessageBox.warning(self, "Error", "No results to export. Run analysis first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "", "CSV (*.csv);;JSON (*.json);;GeoJSON (*.geojson)"
        )
        
        if not file_path:
            return
        
        handler = ExportHandler(self.results, self.layer)
        
        if file_path.endswith(".csv"):
            handler.export_csv(file_path)
        elif file_path.endswith(".json"):
            handler.export_json(file_path)
        elif file_path.endswith(".geojson"):
            handler.export_geojson(file_path)
        
        QMessageBox.information(self, "Success", f"Results exported to:\n{file_path}")
