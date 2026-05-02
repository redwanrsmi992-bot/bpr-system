from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    monthly_cost = db.Column(db.Float, nullable=False)
    working_hours_per_day = db.Column(db.Float, default=8)
    working_days_per_month = db.Column(db.Integer, default=22)
    steps = db.relationship('Step', backref='employee', lazy=True)

    @property
    def cost_per_minute(self):
        total_minutes = self.working_days_per_month * self.working_hours_per_day * 60
        if total_minutes > 0:
            return self.monthly_cost / total_minutes
        return 0

class Process(db.Model):
    __tablename__ = 'processes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    annual_frequency = db.Column(db.Integer, default=1)
    status = db.Column(db.String(30), default='تحت_الدراسة')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    steps = db.relationship('Step', backref='process', lazy=True, order_by='Step.step_order')

    @property
    def total_processing_minutes(self):
        return sum(s.processing_time_minutes or 0 for s in self.steps)

    @property
    def total_wait_minutes(self):
        return sum(s.wait_time_minutes or 0 for s in self.steps)

    @property
    def lead_time_minutes(self):
        return self.total_processing_minutes + self.total_wait_minutes

    @property
    def flow_efficiency(self):
        if self.lead_time_minutes == 0:
            return 0
        return (self.total_processing_minutes / self.lead_time_minutes) * 100

    @property
    def total_cost(self):
        cost = 0
        for step in self.steps:
            if step.employee and step.processing_time_minutes:
                cost_per_min = step.employee.cost_per_minute
                cost += (step.processing_time_minutes * cost_per_min)
        return cost

    @property
    def annual_cost(self):
        return self.total_cost * self.annual_frequency

    @property
    def value_add_ratio(self):
        if not self.steps:
            return 0
        va_steps = sum(1 for s in self.steps if s.step_type == 'VA')
        return (va_steps / len(self.steps)) * 100

    @property
    def waste_summary(self):
        summary = {}
        for step in self.steps:
            if step.step_type == 'NVA' and step.waste_category:
                summary[step.waste_category] = summary.get(step.waste_category, 0) + (step.wait_time_minutes or 0)
        return summary

class Step(db.Model):
    __tablename__ = 'steps'
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    step_order = db.Column(db.Integer, nullable=False)
    step_name = db.Column(db.String(200), nullable=False)
    processing_time_minutes = db.Column(db.Float, default=0)
    wait_time_minutes = db.Column(db.Float, default=0)
    step_type = db.Column(db.String(10), default='VA')
    system_used = db.Column(db.String(50))
    waste_category = db.Column(db.String(50))
    notes = db.Column(db.Text)
