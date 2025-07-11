"""
Parent dashboard for monitoring child sessions
Comprehensive view of all child activities and safety alerts
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QTextEdit,
    QGroupBox, QSplitter, QWidget, QListWidget,
    QListWidgetItem, QProgressBar, QMessageBox,
    QHeaderView, QCalendarWidget
)
from PyQt6.QtCore import (
    Qt, QDate, QTimer, pyqtSignal,
    QPropertyAnimation, QEasingCurve, pyqtSlot
)
from PyQt6.QtGui import QFont, QColor, QBrush, QIcon
from PyQt6.QtCharts import (
    QChart, QChartView, QPieSeries, QBarSeries,
    QBarSet, QValueAxis, QBarCategoryAxis
)

from ..profiles.profile_manager import ProfileManager
from ..constants import APP_NAME


class SessionListItem(QListWidgetItem):
    """Custom list item for session display"""
    
    def __init__(self, session: Dict):
        super().__init__()
        self.session = session
        
        # Format display text
        start_time = datetime.fromisoformat(session['start_time'])
        duration = session.get('duration_minutes', 0)
        questions = session['summary']['total_questions']
        
        display_text = (
            f"{start_time.strftime('%I:%M %p')} - "
            f"{duration} min - "
            f"{questions} questions"
        )
        
        self.setText(display_text)
        
        # Set icon based on safety status
        if session['summary']['safety_incidents'] > 0:
            self.setIcon(QIcon("⚠️"))
            self.setBackground(QBrush(QColor(255, 235, 235)))
        else:
            self.setIcon(QIcon("✅"))


class DashboardSummaryWidget(QWidget):
    """Summary statistics widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Create summary UI"""
        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        
        # Create stat cards
        self.session_card = self.create_stat_card(
            "Total Sessions", "0", "#4CAF50"
        )
        layout.addWidget(self.session_card)
        
        self.time_card = self.create_stat_card(
            "Learning Time", "0 hrs", "#2196F3"
        )
        layout.addWidget(self.time_card)
        
        self.vocab_card = self.create_stat_card(
            "Words Learned", "0", "#FF9800"
        )
        layout.addWidget(self.vocab_card)
        
        self.safety_card = self.create_stat_card(
            "Safety Alerts", "0", "#F44336"
        )
        layout.addWidget(self.safety_card)
        
    def create_stat_card(self, title: str, value: str, color: str) -> QGroupBox:
        """Create a statistics card"""
        card = QGroupBox()
        card.setStyleSheet(f"""
            QGroupBox {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 10px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setObjectName(f"{title.lower().replace(' ', '_')}_value")
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setBold(True)
        value_label.setFont(value_font)
        value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(value_label)
        
        return card
        
    def update_stats(self, stats: Dict):
        """Update statistics display"""
        # Update session count
        sessions_label = self.session_card.findChild(QLabel, "total_sessions_value")
        if sessions_label:
            sessions_label.setText(str(stats.get('total_sessions', 0)))
            
        # Update time
        time_label = self.time_card.findChild(QLabel, "learning_time_value")
        if time_label:
            hours = stats.get('total_hours', 0)
            time_label.setText(f"{hours:.1f} hrs")
            
        # Update vocabulary
        vocab_label = self.vocab_card.findChild(QLabel, "words_learned_value")
        if vocab_label:
            vocab_label.setText(str(stats.get('total_vocabulary', 0)))
            
        # Update safety alerts
        safety_label = self.safety_card.findChild(QLabel, "safety_alerts_value")
        if safety_label:
            safety_label.setText(str(stats.get('safety_incidents', 0)))
            if stats.get('safety_incidents', 0) > 0:
                safety_label.setStyleSheet("color: #F44336;")
            else:
                safety_label.setStyleSheet("color: #4CAF50;")


class ParentDashboard(QDialog):
    """Comprehensive parent dashboard - acts as a 'View' driven by the AppController."""
    
    # Signal to request data from the controller
    data_requested = pyqtSignal(str, str) # child_id, date_range

    def __init__(self, profile_manager: ProfileManager, app_controller, parent=None):
        super().__init__(parent)
        
        self.profile_manager = profile_manager
        self.app_controller = app_controller
        
        self.setWindowTitle(f"{APP_NAME} - Parent Dashboard")
        self.setModal(True)
        self.resize(1200, 800)
        
        self.current_child_id = None
        self.setup_ui()
        self.connect_to_controller()
        self.load_initial_data()
        
    def setup_ui(self):
        """Create dashboard UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Parent Dashboard")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Child selector
        child_label = QLabel("Child:")
        header_layout.addWidget(child_label)
        
        self.child_selector = QComboBox()
        self.child_selector.currentIndexChanged.connect(self.request_data_refresh)
        header_layout.addWidget(self.child_selector)
        
        # Date range selector
        date_label = QLabel("Date Range:")
        header_layout.addWidget(date_label)
        
        self.date_selector = QComboBox()
        self.date_selector.addItems([
            "Today", "Yesterday", "Last 7 Days", 
            "Last 30 Days", "All Time"
        ])
        self.date_selector.currentTextChanged.connect(self.request_data_refresh)
        header_layout.addWidget(self.date_selector)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.request_data_refresh)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Summary statistics
        self.summary_widget = DashboardSummaryWidget()
        layout.addWidget(self.summary_widget)
        
        # Main content tabs
        self.tabs = QTabWidget()
        
        # Sessions tab
        self.sessions_tab = self.create_sessions_tab()
        self.tabs.addTab(self.sessions_tab, "Sessions")
        
        # Learning Progress tab
        self.progress_tab = self.create_progress_tab()
        self.tabs.addTab(self.progress_tab, "Learning Progress")
        
        # Safety tab
        self.safety_tab = self.create_safety_tab()
        self.tabs.addTab(self.safety_tab, "Safety & Alerts")
        
        # Reports tab
        self.reports_tab = self.create_reports_tab()
        self.tabs.addTab(self.reports_tab, "Reports")
        
        layout.addWidget(self.tabs, 1)
        
        # Footer
        footer_layout = QHBoxLayout()
        
        self.status_label = QLabel("Dashboard loaded")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        layout.addLayout(footer_layout)

    def connect_to_controller(self):
        """Connect signals to and from the AppController."""
        self.data_requested.connect(self.app_controller.request_dashboard_data)
        self.app_controller.dashboard_data_ready.connect(self.on_dashboard_data_received)

    def load_initial_data(self):
        """Load the list of children and trigger the first data load."""
        children = self.profile_manager.get_all_children()
        if not children:
            QMessageBox.information(self, "No Children Found", "No child profiles have been created yet.")
            # We can't call self.close() directly here, so we do it via a timer.
            QTimer.singleShot(0, self.close)
            return

        for child in children:
            self.child_selector.addItem(child['name'], child['id'])
        
        # This will trigger the first data load via the currentIndexChanged signal
        self.child_selector.setCurrentIndex(0)

    @pyqtSlot()
    def request_data_refresh(self):
        """Emits a signal to request fresh data from the controller."""
        child_id = self.child_selector.currentData()
        date_range = self.date_selector.currentText()
        if child_id:
            self.current_child_id = child_id
            self.status_label.setText(f"Loading data for {self.child_selector.currentText()}...")
            self.data_requested.emit(child_id, date_range)

    @pyqtSlot(dict)
    def on_dashboard_data_received(self, data: dict):
        """Slot to receive and display the processed dashboard data from the controller."""
        self.status_label.setText("Dashboard data loaded successfully.")
        
        # Update summary stats
        self.summary_widget.update_stats(data.get('stats', {}))

        # Update session list
        self.update_session_list(data.get('sessions', []))
        
        # Update progress charts (simplified for this refactor)
        # In a real app, you might pass more structured data for charts
        self.update_topics_chart(data['stats'].get('topic_counts', {}))

        # Update safety tab
        self.update_safety_tab(data.get('safety_report', {}))

    def create_sessions_tab(self) -> QWidget:
        """Create sessions view tab"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left side - session list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        sessions_label = QLabel("Sessions")
        sessions_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(sessions_label)
        
        self.session_list_widget = QListWidget()
        self.session_list_widget.currentItemChanged.connect(self.on_session_selected)
        left_layout.addWidget(self.session_list_widget)
        
        # Right side - session details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        details_label = QLabel("Session Details")
        details_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(details_label)
        
        self.session_detail_area = QTextEdit()
        self.session_detail_area.setReadOnly(True)
        right_layout.addWidget(self.session_detail_area)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        return widget
        
    def create_progress_tab(self) -> QWidget:
        """Create learning progress tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Progress charts
        charts_layout = QHBoxLayout()
        
        # Topics chart
        self.topics_chart = self.create_topics_chart()
        charts_layout.addWidget(self.topics_chart)
        
        # Time chart
        self.time_chart = self.create_time_chart()
        charts_layout.addWidget(self.time_chart)
        
        layout.addLayout(charts_layout)
        
        # Vocabulary and concepts
        details_group = QGroupBox("Learning Details")
        details_layout = QHBoxLayout()
        
        # Vocabulary list
        vocab_widget = QWidget()
        vocab_layout = QVBoxLayout(vocab_widget)
        
        vocab_label = QLabel("New Vocabulary")
        vocab_label.setStyleSheet("font-weight: bold;")
        vocab_layout.addWidget(vocab_label)
        
        self.vocab_list = QListWidget()
        vocab_layout.addWidget(self.vocab_list)
        
        details_layout.addWidget(vocab_widget)
        
        # Concepts list
        concepts_widget = QWidget()
        concepts_layout = QVBoxLayout(concepts_widget)
        
        concepts_label = QLabel("Concepts Explored")
        concepts_label.setStyleSheet("font-weight: bold;")
        concepts_layout.addWidget(concepts_label)
        
        self.concepts_list = QListWidget()
        concepts_layout.addWidget(self.concepts_list)
        
        details_layout.addWidget(concepts_widget)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        return widget
        
    def create_safety_tab(self) -> QWidget:
        """Create safety monitoring tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Safety alerts table
        alerts_label = QLabel("Safety Alerts & Incidents")
        alerts_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(alerts_label)
        
        self.safety_alerts_list = QListWidget()
        layout.addWidget(self.safety_alerts_list)
        
        # Safety statistics
        stats_group = QGroupBox("Safety Statistics")
        stats_layout = QHBoxLayout()
        
        # Create safety stat displays
        self.safety_stats = {}
        for stat_name in ["Total Alerts", "This Week", "Redirects", "Strikes"]:
            stat_widget = self.create_safety_stat(stat_name)
            stats_layout.addWidget(stat_widget)
            self.safety_stats[stat_name.lower().replace(' ', '_')] = stat_widget
            
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        return widget
        
    def create_reports_tab(self) -> QWidget:
        """Create reports generation tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Report options
        options_group = QGroupBox("Report Options")
        options_layout = QVBoxLayout()
        
        # Report type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Report Type:"))
        
        self.report_type = QComboBox()
        self.report_type.addItems([
            "Daily Summary",
            "Weekly Progress",
            "Monthly Overview",
            "Safety Report",
            "Learning Milestones"
        ])
        type_layout.addWidget(self.report_type)
        type_layout.addStretch()
        
        options_layout.addLayout(type_layout)
        
        # Date selection
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date:"))
        
        self.report_date = QDateEdit()
        self.report_date.setCalendarPopup(True)
        self.report_date.setDate(QDate.currentDate())
        date_layout.addWidget(self.report_date)
        date_layout.addStretch()
        
        options_layout.addLayout(date_layout)
        
        # Generate button
        generate_btn = QPushButton("Generate Report")
        generate_btn.clicked.connect(self.generate_report)
        options_layout.addWidget(generate_btn)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Report display
        self.report_display = QTextEdit()
        self.report_display.setReadOnly(True)
        layout.addWidget(self.report_display)
        
        # Export buttons
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        
        export_pdf_btn = QPushButton("Export as PDF")
        export_pdf_btn.clicked.connect(self.export_pdf)
        export_layout.addWidget(export_pdf_btn)
        
        export_csv_btn = QPushButton("Export as CSV")
        export_csv_btn.clicked.connect(self.export_csv)
        export_layout.addWidget(export_csv_btn)
        
        layout.addLayout(export_layout)
        
        return widget
        
    def create_topics_chart(self) -> QChartView:
        """Create topics distribution chart"""
        series = QPieSeries()
        
        # Placeholder data
        series.append("Science", 35)
        series.append("Math", 25)
        series.append("Technology", 20)
        series.append("Engineering", 20)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Topics Explored")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(chart_view.renderHints() | 
                                chart_view.RenderHint.Antialiasing)
        
        return chart_view
        
    def create_time_chart(self) -> QChartView:
        """Create time spent chart"""
        series = QBarSeries()
        
        # Placeholder data
        set0 = QBarSet("Learning Time")
        set0.append([30, 45, 60, 40, 55, 35, 50])  # Minutes per day
        
        series.append(set0)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Daily Learning Time (Past Week)")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        # Axes
        categories = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d min")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(chart_view.renderHints() | 
                                chart_view.RenderHint.Antialiasing)
        
        return chart_view
        
    def create_safety_stat(self, name: str) -> QWidget:
        """Create a safety statistic widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel(name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        value = QLabel("0")
        value.setObjectName("value")
        value_font = QFont()
        value_font.setPointSize(20)
        value_font.setBold(True)
        value.setFont(value_font)
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value)
        
        widget.setStyleSheet("""
            QWidget {
                background-color: #FFF3E0;
                border: 1px solid #FFB74D;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        return widget
        
    def on_session_selected(self, current: SessionListItem, previous: Optional[SessionListItem]):
        """Display details for the selected session."""
        if current:
            self.display_session_details(current.session)

    def display_session_details(self, session: Dict):
        """Formats and displays the details of a single session."""
        details = session.get('details', {})
        summary = session.get('summary', {})
        
        start_time = datetime.fromisoformat(session['start_time']).strftime('%Y-%m-%d %I:%M %p')
        
        # Build a detailed HTML report for the text area
        report = f"""
        <h3>Session Details</h3>
        <b>Time:</b> {start_time}<br>
        <b>Duration:</b> {session.get('duration_minutes', 0)} minutes<br>
        
        <h4>Summary</h4>
        - <b>Questions Asked:</b> {summary.get('total_questions', 0)}<br>
        - <b>Topics Discussed:</b> {', '.join(summary.get('topics', ['N/A']))}<br>
        
        <h4>Conversation</h4>
        """
        
        conversation = details.get('conversation', [])
        if not conversation:
            report += "<p><i>No conversation logged for this session.</i></p>"
        else:
            for entry in conversation:
                author = "<b>You:</b>" if entry['author'] == 'user' else "<b>Sunflower AI:</b>"
                report += f"<p>{author} {entry['text']}</p>"
        
        self.session_detail_area.setHtml(report)

    def update_session_list(self, sessions: List[Dict]):
        """Populates the session list widget with new session data."""
        self.session_list_widget.clear()
        if not sessions:
            self.session_detail_area.setText("No sessions found for the selected period.")
            return

        for session in sorted(sessions, key=lambda s: s['start_time'], reverse=True):
            item = SessionListItem(session)
            self.session_list_widget.addItem(item)
            
        # Select the first item by default
        if self.session_list_widget.count() > 0:
            self.session_list_widget.setCurrentRow(0)

    def update_progress_tab(self, sessions: List[Dict]):
        pass # This will be driven by on_dashboard_data_received

    def update_topics_chart(self, topic_counts: Dict[str, int]):
        """Updates the topics pie chart with new data."""
        series = self.topics_chart.series()[0]
        series.clear()
        
        for topic, count in topic_counts.items():
            series.append(topic, count)
            
    def update_safety_tab(self, safety_report: dict):
        """Updates the safety tab with new data."""
        self.safety_alerts_list.clear()
        alerts = safety_report.get("alerts", [])
        
        if not alerts:
            self.safety_alerts_list.addItem("No safety alerts in this period.")
            return

        for alert in alerts:
            timestamp = datetime.fromisoformat(alert['timestamp']).strftime('%Y-%m-%d %I:%M %p')
            self.safety_alerts_list.addItem(f"[{timestamp}] {alert['details']} (Category: {alert['category']})")
        
    def generate_report(self):
        """Generate selected report"""
        report_type = self.report_type.currentText()
        report_date = self.report_date.date()
        
        # Generate report based on type
        if report_type == "Daily Summary":
            report = self.generate_daily_summary(report_date)
        elif report_type == "Weekly Progress":
            report = self.generate_weekly_progress(report_date)
        elif report_type == "Monthly Overview":
            report = self.generate_monthly_overview(report_date)
        elif report_type == "Safety Report":
            report = self.generate_safety_report(report_date)
        else:  # Learning Milestones
            report = self.generate_milestones_report()
            
        self.report_display.setPlainText(report)
        
    def generate_daily_summary(self, date: QDate) -> str:
        """Generate daily summary report"""
        date_str = date.toString("yyyy-MM-dd")
        
        report = f"""
SUNFLOWER AI - DAILY SUMMARY REPORT
{date.toString("MMMM d, yyyy")}
{'=' * 60}

"""
        
        # Get sessions for the date
        if self.current_child_id:
            child = self.profile_manager.get_child(self.current_child_id)
            child_name = child['name'] if child else "Unknown"
            
            summary = self.session_logger.get_daily_summary(
                self.current_child_id,
                datetime.strptime(date_str, "%Y-%m-%d")
            )
            
            report += f"Child: {child_name}\n\n"
            report += f"Total Sessions: {summary['total_sessions']}\n"
            report += f"Total Time: {summary['total_time_minutes']} minutes\n"
            report += f"Questions Asked: {summary['total_questions']}\n"
            report += f"Safety Incidents: {summary['safety_incidents']}\n\n"
            
            if summary['unique_topics']:
                report += "Topics Explored:\n"
                for topic in summary['unique_topics']:
                    report += f"  • {topic}\n"
                report += "\n"
                
            if summary['new_vocabulary']:
                report += "New Vocabulary:\n"
                for word in summary['new_vocabulary'][:10]:
                    report += f"  • {word}\n"
                if len(summary['new_vocabulary']) > 10:
                    report += f"  ... and {len(summary['new_vocabulary']) - 10} more\n"
                    
        else:
            report += "Please select a specific child for detailed daily summary.\n"
            
        report += "\n" + "=" * 60 + "\n"
        report += "Generated: " + datetime.now().strftime("%Y-%m-%d %I:%M %p")
        
        return report
        
    def generate_weekly_progress(self, end_date: QDate) -> str:
        """Generate weekly progress report"""
        # Implementation similar to daily but for week
        return "Weekly Progress Report\n[Report content would be generated here]"
        
    def generate_monthly_overview(self, month_date: QDate) -> str:
        """Generate monthly overview report"""
        # Implementation for monthly report
        return "Monthly Overview Report\n[Report content would be generated here]"
        
    def generate_safety_report(self, date: QDate) -> str:
        """Generate safety report"""
        # Implementation for safety report
        return "Safety Report\n[Report content would be generated here]"
        
    def generate_milestones_report(self) -> str:
        """Generate learning milestones report"""
        # Implementation for milestones report
        return "Learning Milestones Report\n[Report content would be generated here]"
        
    def export_pdf(self):
        """Export report as PDF"""
        QMessageBox.information(
            self,
            "Export PDF",
            "PDF export functionality would be implemented here.\n"
            "The report would be formatted and saved as a PDF file."
        )
        
    def export_csv(self):
        """Export data as CSV"""
        QMessageBox.information(
            self,
            "Export CSV",
            "CSV export functionality would be implemented here.\n"
            "Session data would be exported in spreadsheet format."
        )
        
    def closeEvent(self, event):
        self.accept()
