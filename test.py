import os
import datetime
from dotenv import load_dotenv
from fastmcp import FastMCP
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func

# Load environment variables from .env file
load_dotenv()
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")
Database_url = os.getenv('DATABASE_URL')
# pool_pre_ping=True checks if connections are alive before using them
engine = create_engine(Database_url, pool_pre_ping=True, pool_recycle=300)
session=sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    sub_category = Column(String)
    notes = Column(String)
    
Base.metadata.create_all(engine)

mcp = FastMCP("NeonExpenseTracker")

@mcp.tool
def add_expense(date: str, amount: float, category: str, sub_category: str = None, notes: str = None) -> str:
    """Add a new expense to the database."""
    db = session()
    try:
        expense_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        new_expense = Expense(date=expense_date, amount=amount, category=category, sub_category=sub_category, notes=notes)
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        return f"Expense added successfully with ID: {new_expense.id}"
    except Exception as e:
        db.rollback()
        return f"Error adding expense: {str(e)}"
    finally:
        db.close()

@mcp.tool
def list_expenses(start_date: str, end_date: str) -> list[dict]:
    """List expenses between two dates."""
    db = session()
    try:
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        expenses = db.query(Expense).filter(Expense.date.between(start, end)).all()
        return [{"id": exp.id, "date": exp.date.isoformat(), "amount": exp.amount, "category": exp.category, "sub_category": exp.sub_category, "notes": exp.notes} for exp in expenses]
    except Exception as e:
        return [{"error": f"Error listing expenses: {str(e)}"}]
    finally:
        db.close()
    
@mcp.tool()
def summarize_expenses(start_date: str, end_date: str, category: str = None) -> str:
    """Summarize total expenses within a date range (YYYY-MM-DD), optionally filtered by category."""
    try:
        s_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        
        with session() as db:
            # SQLAlchemy Query replacing the raw SQL "SELECT SUM(amount)..."
            query = db.query(func.sum(Expense.amount)).filter(Expense.date.between(s_date, e_date))
            
            # Dynamically add the category filter if provided
            if category:
                query = query.filter(Expense.category == category)
                
            total = query.scalar() or 0.0
            
            if category:
                return f"Total spent on {category} between {start_date} and {end_date}: ₹{total:.2f}"
            else:
                return f"Total overall expenses between {start_date} and {end_date}: ₹{total:.2f}"
                
    except Exception as e:
        return f"Database error summarizing expenses: {str(e)}"
@mcp.tool
def delete_expense(expense_id: int) -> str:
    """Delete an expense by its ID."""
    db = session()
    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            return f"No expense found with ID: {expense_id}"
        db.delete(expense)
        db.commit()
        return f"Expense with ID: {expense_id} deleted successfully."
    except Exception as e:
        db.rollback()
        return f"Error deleting expense: {str(e)}"
    finally:
        db.close()

@mcp.tool
def edit_expense(expense_id: int, date: str = None, amount: float = None, category: str = None, sub_category: str = None, notes: str = None) -> str:
    """Edit an existing expense by its ID."""
    db = session()
    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            return f"No expense found with ID: {expense_id}"
        
        if date:
            expense.date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        if amount is not None:
            expense.amount = amount
        if category:
            expense.category = category
        if sub_category is not None:
            expense.sub_category = sub_category
        if notes is not None:
            expense.notes = notes
        
        db.commit()
        return f"Expense with ID: {expense_id} updated successfully."
    except Exception as e:
        db.rollback()
        return f"Error editing expense: {str(e)}"
    finally:
        db.close()


@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()
    
if __name__ == "__main__":
        mcp.run(transport="http", host="0.0.0.0", port=8000)
