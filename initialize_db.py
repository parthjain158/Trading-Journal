from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Assuming your models are defined in a separate file called models.py
# from models import Trade, Market, TradeSetup, AccountBalanceLog

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Market(db.Model):
    __tablename__ = 'markets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

class TradeSetup(db.Model):
    __tablename__ = 'trade_setups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))

class Trade(db.Model):
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True)
    date_entered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_exited = db.Column(db.DateTime)
    asset = db.Column(db.String(50), nullable=False)
    market_id = db.Column(db.Integer, db.ForeignKey('markets.id'), nullable=False)
    direction = db.Column(db.String(10))
    trade_setup_id = db.Column(db.Integer, db.ForeignKey('trade_setups.id'))
    number_of_confluences = db.Column(db.Integer)
    planned_return = db.Column(db.Float)
    actual_return = db.Column(db.Float)
    risk = db.Column(db.Float)
    position_size = db.Column(db.Integer)
    pre_trade_notes = db.Column(db.Text)
    post_trade_notes = db.Column(db.Text)
    feelings_after_trade = db.Column(db.Text)

class AccountBalanceLog(db.Model):
    __tablename__ = 'account_balance_logs'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    balance = db.Column(db.Float, nullable=False)

def recreate_database():
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating tables...")
        db.create_all()
        populate_sample_data()
        print("Database has been reset and initialized.")

def populate_sample_data():
    with app.app_context():
        markets = [Market(name="Forex"), Market(name="Stocks"), Market(name="Cryptocurrency"), Market(name="Options")]
        db.session.add_all(markets)

        trade_setups = [
            TradeSetup(name="Range Breakout", description="Setup for trading range breakouts."),
            TradeSetup(name="Swing Failure", description="Setup for identifying swing failure patterns."),
            TradeSetup(name="Trend Continuation", description="Setup for riding the trend."),
            TradeSetup(name="Order Blocks", description="Setup for trading based on order blocks.")
        ]
        db.session.add_all(trade_setups)

        # Add more sample data as needed

        db.session.commit()
        print("Sample data added successfully.")

if __name__ == '__main__':
    recreate_database()
