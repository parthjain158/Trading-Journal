from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_migrate import Migrate
from flask import Flask, request, jsonify, render_template
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trading_journal_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Global Risk Percentage (default to 2%)
global_risk_percentage = 0.02

# Models
class TradeSetup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)  # Positive for deposits, negative for withdrawals
    date = db.Column(db.DateTime, default=datetime.utcnow)
    type = db.Column(db.String(10), nullable=False)  # 'deposit' or 'withdrawal'

class Market(db.Model):
    __tablename__ = 'market'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class AccountBalanceLog(db.Model):
    __tablename__ = 'account_balance_log'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)  # Ensure one entry per day
    balance = db.Column(db.Float, nullable=False)  # Account balance for the day


# This relationship will allow linking multiple setups to a trade if needed
trade_setups = db.Table('trade_setups',
    db.Column('trade_id', db.Integer, db.ForeignKey('trade.id'), primary_key=True),
    db.Column('setup_id', db.Integer, db.ForeignKey('trade_setup.id'), primary_key=True)
)

class Trade(db.Model):
    __tablename__ = 'trade'
    id = db.Column(db.Integer, primary_key=True)
    date_entered = db.Column(db.DateTime)
    date_exited = db.Column(db.DateTime, nullable=True)
    asset = db.Column(db.String(50), nullable=False)
    market_id = db.Column(db.Integer, db.ForeignKey('market.id'), nullable=False)
    market = db.relationship('Market', backref='trades')  # Relationship to Market
    direction = db.Column(db.String(10), nullable=False)  # Long or Short
    trade_setup_id = db.Column(db.Integer, db.ForeignKey('trade_setup.id'), nullable=False)
    trade_setup = db.relationship('TradeSetup', backref='trades')  # Relationship to TradeSetup
    number_of_confluences = db.Column(db.Integer)
    planned_rr = db.Column(db.Float)
    planned_return = db.Column(db.Float)
    actual_rr = db.Column(db.Float, nullable=True)
    actual_return = db.Column(db.Float, nullable=True)
    risk = db.Column(db.Float)
    position_size = db.Column(db.Float)
    roi_on_position = db.Column(db.Float, nullable=True)
    account_change = db.Column(db.Float, nullable=True)
    account_change_percentage = db.Column(db.Float, nullable=True)
    cumulative_pnl = db.Column(db.Float, nullable=True)
    account_balance = db.Column(db.Float, nullable=True)
    pre_trade_notes = db.Column(db.Text, nullable=True)
    post_trade_notes = db.Column(db.Text, nullable=True)
    feelings_after_trade = db.Column(db.Text, nullable=True)


# Global Risk Percentage Management
@app.route('/set_risk', methods=['POST'])
def set_risk():
    global global_risk_percentage  # Ensure the variable is declared as global at the beginning
    data = request.json
    global_risk_percentage = data.get('risk_percentage')

    if not (0 < global_risk_percentage <= 1):
        return jsonify({'error': 'Risk percentage must be between 0 and 1'}), 400

    # Set risk percentage globally for this session
    return jsonify({'message': f'Risk percentage set to {global_risk_percentage * 100}%'})

@app.route('/get_risk', methods=['GET'])
def get_risk():
    return jsonify({'risk_percentage': global_risk_percentage})

# Tag Management Routes
@app.route('/add_trade_setup', methods=['POST'])
def add_trade_setup():
    data = request.json  # Expecting a dictionary or list

    # Check if data is a list (batch addition)
    if isinstance(data, list):
        setups = []
        for item in data:
            if 'name' in item and 'description' in item:
                setup = TradeSetup(name=item['name'], description=item['description'])
                db.session.add(setup)
                setups.append(setup.name)
            else:
                return jsonify({"error": "Each setup object must include 'name' and 'description' fields"}), 400

        db.session.commit()
        return jsonify({"message": "Trade setups added successfully", "setups": setups}), 201

    # Handle single setup addition
    elif isinstance(data, dict):
        setup_name = data.get('name')
        description = data.get('description')

        if not setup_name or not description:
            return jsonify({"error": "Both 'name' and 'description' are required"}), 400

        setup = TradeSetup(name=setup_name, description=description)
        db.session.add(setup)
        db.session.commit()
        return jsonify({"message": "Trade setup added successfully", "setup_id": setup.id}), 201

    # Invalid format
    else:
        return jsonify({"error": "Invalid data format. Expected a JSON object or list."}), 400

@app.route('/get_trade_setups', methods=['GET'])
def get_trade_setups():
    setups = TradeSetup.query.all()
    return jsonify([{'id': setup.id, 'name': setup.name, 'description': setup.description} for setup in setups])

@app.route('/delete_trade_setup', methods=['DELETE'])
def delete_trade_setup():
    setup_id = request.args.get('id')
    setup = TradeSetup.query.get(setup_id)
    if not setup:
        return jsonify({'error': 'Trade setup not found'}), 404

    db.session.delete(setup)
    db.session.commit()
    return jsonify({'message': 'Trade setup deleted successfully'})

# Market Management Routes
@app.route('/add_market', methods=['POST'])
def add_market():
    data = request.json  # Expecting a dictionary or list

    # Check if data is a list (batch addition)
    if isinstance(data, list):
        markets = []
        for item in data:
            if 'name' in item:
                market = Market(name=item['name'])
                db.session.add(market)
                markets.append(market.name)
            else:
                return jsonify({"error": "Each market object must include a 'name' field"}), 400

        db.session.commit()
        return jsonify({"message": f"Markets added successfully", "markets": markets}), 201

    # Handle single market addition
    elif isinstance(data, dict):
        market_name = data.get('name')
        if not market_name:
            return jsonify({"error": "Market 'name' is required"}), 400

        # Create and add market
        market = Market(name=market_name)
        db.session.add(market)
        db.session.commit()
        return jsonify({"message": "Market added successfully", "market_id": market.id}), 201

    # Invalid format
    else:
        return jsonify({"error": "Invalid data format. Expected a JSON object or list."}), 400


@app.route('/get_markets', methods=['GET'])
def get_markets():
    markets = Market.query.all()
    return jsonify([{'id': m.id, 'name': m.name} for m in markets])

@app.route('/delete_market', methods=['DELETE'])
def delete_market():
    market_id = request.args.get('id')
    market = Market.query.get(market_id)
    if not market:
        return jsonify({'error': 'Market not found'}), 404

    db.session.delete(market)
    db.session.commit()
    return jsonify({'message': 'Market deleted successfully'})

#Trade management routes
@app.route('/add_trade', methods=['POST'])
def add_trade():
    data = request.json
    trade_ids = []

    # Handle batch addition if input is a list
    if isinstance(data, list):
        for item in data:
            try:
                process_trade(item, trade_ids)
            except KeyError as e:
                return jsonify({"error": f"Missing required field: {str(e)}"}), 400
        db.session.commit()
        return jsonify({"message": "Trades added successfully", "trade_ids": trade_ids}), 201

    # Handle single trade addition if input is a dictionary
    elif isinstance(data, dict):
        try:
            process_trade(data, trade_ids)
            db.session.commit()
            return jsonify({"message": "Trade added successfully", "trade_id": trade_ids[0]}), 201
        except KeyError as e:
            return jsonify({"error": f"Missing required field: {str(e)}"}), 400

    # Invalid format
    else:
        return jsonify({"error": "Invalid data format. Expected a JSON object or list."}), 400

def process_trade(data, trade_ids):
    # Parse dates
    date_entered = datetime.strptime(data['date_entered'], "%Y-%m-%dT%H:%M:%S") if 'date_entered' in data and data['date_entered'] else datetime.utcnow()
    date_exited = datetime.strptime(data['date_exited'], "%Y-%m-%dT%H:%M:%S") if 'date_exited' in data and data['date_exited'] else None

    # Automatic calculations
    risk = data.get('risk', 1)
    planned_return = data.get('planned_return', 0)
    actual_return = data.get('actual_return', 0)
    planned_rr = (planned_return / risk) if risk > 0 else 0
    actual_rr = (actual_return / risk) if risk > 0 else 0

    # Retrieve previous trade's balance and cumulative P&L
    previous_trade = Trade.query.order_by(Trade.id.desc()).first()
    previous_balance = previous_trade.account_balance if previous_trade else 1000  # Default starting balance
    result = data.get('result', 0)  # Result is the profit/loss from the trade

    new_account_balance = previous_balance + result
    cumulative_pnl = previous_trade.cumulative_pnl + result if previous_trade else result

    # Create trade object
    trade = Trade(
        date_entered=date_entered,
        date_exited=date_exited,
        asset=data['asset'],
        market_id=data['market_id'],
        direction=data['direction'],
        trade_setup_id=data['trade_setup_id'],
        number_of_confluences=data['number_of_confluences'],
        planned_rr=planned_rr,
        planned_return=planned_return,
        actual_rr=actual_rr,
        actual_return=actual_return,
        risk=risk,
        position_size=data['position_size'],
        roi_on_position=(result / risk * 100) if risk > 0 else 0,
        account_change=result,
        account_change_percentage=(result / previous_balance * 100) if previous_balance != 0 else 0,
        cumulative_pnl=cumulative_pnl,
        account_balance=new_account_balance,
        pre_trade_notes=data.get('pre_trade_notes'),
        post_trade_notes=data.get('post_trade_notes'),
        feelings_after_trade=data.get('feelings_after_trade')
    )
    db.session.add(trade)
    trade_ids.append(trade.id)

    # Log daily balance
    log_daily_balance(date_entered, new_account_balance)



@app.route('/get_trades', methods=['GET'])
def get_trades():
    trades = Trade.query.all()
    trades_data = []
    for trade in trades:
        trades_data.append({
            "id": trade.id,
            "date_entered": trade.date_entered.strftime("%Y-%m-%dT%H:%M:%S") if trade.date_entered else None,
            "date_exited": trade.date_exited.strftime("%Y-%m-%dT%H:%M:%S") if trade.date_exited else None,
            "asset": trade.asset,
            "market_name": trade.market.name if trade.market else "Unknown",  # Handle missing market
            "direction": trade.direction,
            "trade_setup_name": trade.trade_setup.name if trade.trade_setup else "Unknown",  # Handle missing trade setup
            "number_of_confluences": trade.number_of_confluences,
            "planned_rr": trade.planned_rr,
            "planned_return": trade.planned_return,
            "actual_rr": trade.actual_rr,
            "actual_return": trade.actual_return,
            "risk": trade.risk,
            "position_size": trade.position_size,
            "roi_on_position": trade.roi_on_position,
            "account_change": trade.account_change,
            "account_change_percentage": trade.account_change_percentage,
            "cumulative_pnl": trade.cumulative_pnl,
            "account_balance": trade.account_balance,
            "pre_trade_notes": trade.pre_trade_notes,
            "post_trade_notes": trade.post_trade_notes,
            "feelings_after_trade": trade.feelings_after_trade
        })
    return jsonify(trades_data)


@app.route('/delete_trade/<int:trade_id>', methods=['DELETE'])
def delete_trade(trade_id):
    trade = Trade.query.get(trade_id)
    if not trade:
        return jsonify({'error': 'Trade not found'}), 404  # Trade not found

    db.session.delete(trade)
    db.session.commit()
    return jsonify({'message': 'Trade deleted successfully'}), 200

def log_daily_balance(date, balance):
    # This function should correctly update or create a balance log for the day
    balance_log = AccountBalanceLog.query.filter_by(date=date.date()).first()
    if balance_log:
        balance_log.balance = balance  # Update existing log
    else:
        new_log = AccountBalanceLog(date=date.date(), balance=balance)  # Create new log
        db.session.add(new_log)
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)


@app.route('/metrics', methods=['GET'])
def metrics():
    trades = Trade.query.order_by(Trade.id.asc()).all()
    if not trades:
        return jsonify({"message": "No trades available to calculate metrics"}), 200

    # Initialize variables for calculations
    total_trades = len(trades)
    winning_trades = sum(1 for trade in trades if trade.actual_return is not None and trade.actual_return > 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    cumulative_pnl = sum(trade.actual_return for trade in trades if trade.actual_return is not None)
    avg_planned_rr = sum(trade.planned_rr for trade in trades if trade.planned_rr is not None) / total_trades if total_trades > 0 else 0
    avg_actual_rr = sum(trade.actual_rr for trade in trades if trade.actual_rr is not None) / total_trades if total_trades > 0 else 0

    # Dynamically calculate account balance based on trades
    starting_balance = 1000  # Assume a starting balance
    account_balance = starting_balance
    for trade in trades:
        if trade.actual_return is not None:
            account_balance += trade.actual_return

    account_balance_change = account_balance - starting_balance

    avg_account_change_percentage = sum(
        trade.account_change_percentage for trade in trades if trade.account_change_percentage is not None
    ) / total_trades if total_trades > 0 else 0

    largest_win = max((trade.actual_return for trade in trades if trade.actual_return is not None), default=0)
    largest_loss = min((trade.actual_return for trade in trades if trade.actual_return is not None), default=0)

    setup_counts = {}
    for trade in trades:
        setup_name = trade.trade_setup.name if trade.trade_setup else "Unknown"
        setup_counts[setup_name] = setup_counts.get(setup_name, 0) + 1
    most_common_setup = max(setup_counts, key=setup_counts.get) if setup_counts else "None"

    market_counts = {}
    for trade in trades:
        market_name = trade.market.name if trade.market else "Unknown"
        market_counts[market_name] = market_counts.get(market_name, 0) + 1
    most_traded_market = max(market_counts, key=market_counts.get) if market_counts else "None"

    # Construct the response
    metrics_data = {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "cumulative_pnl": cumulative_pnl,
        "average_planned_rr": avg_planned_rr,
        "average_actual_rr": avg_actual_rr,
        "account_balance": account_balance,
        "account_balance_change": account_balance_change,
        "average_account_change_percentage": avg_account_change_percentage,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "most_common_setup": most_common_setup,
        "most_traded_market": most_traded_market
    }

    return jsonify(metrics_data), 200


@app.route('/add_deposit', methods=['POST'])
def add_deposit():
    data = request.json
    if not data or 'amount' not in data:
        return jsonify({'error': 'Amount is required.'}), 400

    try:
        amount = float(data['amount'])  # Convert to float
    except ValueError:
        return jsonify({'error': 'Amount must be a valid number.'}), 400

    if amount <= 0:
        return jsonify({'error': 'Amount must be greater than 0.'}), 400

    # Add deposit logic
    new_deposit = Transaction(amount=amount, type='deposit')
    db.session.add(new_deposit)
    db.session.commit()

    return jsonify({'message': f'Deposit of {amount} added successfully!'})


@app.route('/get_transactions', methods=['GET'])
def get_transactions():
    transactions = Transaction.query.all()
    return jsonify([
        {
            'id': t.id,
            'amount': t.amount,
            'type': t.type,
            'date': t.date.strftime('%Y-%m-%d %H:%M:%S')
        } for t in transactions
    ])

@app.route('/add_withdrawal', methods=['POST'])
def add_withdrawal():
    data = request.json
    amount = float(data['amount'])

    if not amount or amount <= 0:
        return jsonify({'error': 'Invalid withdrawal amount'}), 400

    # Add withdrawal to the database
    withdrawal = Transaction(amount=-amount, type='withdrawal')
    db.session.add(withdrawal)

    # Update the account balance for the most recent trade
    last_trade = Trade.query.order_by(Trade.id.desc()).first()
    new_balance = (last_trade.account_balance if last_trade else 0) - amount

    if new_balance < 0:
        return jsonify({'error': 'Withdrawal would result in negative balance'}), 400

    if last_trade:
        last_trade.account_balance = new_balance

    db.session.commit()

    return jsonify({'message': 'Withdrawal recorded successfully', 'new_balance': new_balance})

@app.route('/system_settings')
def system_settings():
    return render_template('system_settings.html')


# Database Initialization
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)

@app.route('/')
@app.route('/dashboard')
def dashboard():
    trades = Trade.query.all()
    labels = [t.date.strftime('%Y-%m-%d') for t in trades]
    account_balances = [t.account_balance for t in trades]
    return render_template('dashboard.html', labels=labels, account_balances=account_balances)

@app.route('/trades')
def trades():
    all_trades = Trade.query.all()
    return render_template('trades.html', trades=all_trades)

@app.route('/transactions')
def transactions():
    return render_template('transactions.html')

@app.route('/tags')
def tags():
    return render_template('tags.html')

@app.route('/markets')
def markets():
    return render_template('markets.html')

