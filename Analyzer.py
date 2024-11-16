import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
from datetime import datetime
import tempfile
import os

# Page configuration (must be first)
st.set_page_config(page_title="Transaction Analyzer", layout="wide")

# Predefined user credentials
USER_CREDENTIALS = {
    "FroTest": "FroTest123",
    "ForRushi": "ForRushi",
    "ForFriends": "ForFriends123", 
    "AskedRushi?": "HeSaidYes",
    "hMMMMM":"HHHHHm"
}

def login():
    """Login page for user authentication."""
    st.title("🔒 Login Page")
    username = st.text_input("Enter your Username")
    password = st.text_input("Enter your Password", type="password")
    login_button = st.button("Login")

    if login_button:
        if username in USER_CREDENTIALS and password == USER_CREDENTIALS[username]:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid username or password. Please try again.")

def logout():
    """Logout function."""
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""

class TransactionAnalyzer:
    def __init__(self, pdf_path: str, language: str = 'en'):
        self.transactions = self._parse_transactions(pdf_path)
        self.language = language
        self.filtered_transactions = self.transactions

    def filter_by_date(self, start_date: datetime, end_date: datetime):
        """Filter transactions by date range."""
        if not start_date or not end_date:
            self.filtered_transactions = self.transactions
            return self.filtered_transactions
            
        self.filtered_transactions = [
            t for t in self.transactions
            if start_date.date() <= t['date'].date() <= end_date.date()
        ]
        return self.filtered_transactions
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string with error handling."""
        try:
            date_str = date_str.strip()
            return datetime.strptime(date_str, '%b %d, %Y')  # Adjust format as needed
        except ValueError as e:
            st.warning(f"Warning: Unable to parse date '{date_str}'.")
            return None

    def _parse_transactions(self, pdf_path: str) -> list:
        """Parse all transactions from the PDF file."""
        transactions = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    st.warning(f"Warning: Page {page_number + 1} is empty or could not be read.")
                    continue
                
                for line_number, line in enumerate(text.split('\n')):
                    try:
                        date_str = line[:12].strip()  # Assuming date is the first 12 characters
                        amount_index = line.rfind('₹')
                        if amount_index == -1:
                            continue  # Skip lines without an amount symbol

                        amount_str = line[amount_index + 1:].strip().replace(',', '')  # Remove commas in amounts
                        description = line[12:amount_index].strip()
                        transaction_type = 'CREDIT' if 'CREDIT' in line.upper() else 'DEBIT'

                        amount = float(amount_str)
                        date = self._parse_date(date_str)
                        if date is None:
                            continue  # Skip if date parsing fails

                        transactions.append({
                            'date': date,
                            'description': description,
                            'type': transaction_type,
                            'amount': amount
                        })
                    except Exception as e:
                        st.warning(f"Warning: Failed to process line '{line}' on page {page_number + 1}.")
                        st.error(e)
                        continue

        return sorted(transactions, key=lambda x: x['date'], reverse=True) if transactions else []

    def get_total_spending(self):
        return sum(t['amount'] for t in self.filtered_transactions if t['type'] == 'DEBIT')

    def get_total_income(self):
        return sum(t['amount'] for t in self.filtered_transactions if t['type'] == 'CREDIT')

    def get_balance(self):
        return self.get_total_income() - self.get_total_spending()

    def get_merchant_analysis(self) -> list:
        """Analyze spending by merchant."""
        from collections import defaultdict
        merchant_spending = defaultdict(float)
        for t in self.filtered_transactions:
            if t['type'] == 'DEBIT':
                merchant_spending[t['description']] += t['amount']
        return sorted(merchant_spending.items(), key=lambda x: x[1], reverse=True)

def create_charts(analyzer):
    df = pd.DataFrame([{
        'date': t['date'].strftime('%Y-%m-%d') if t['date'] else "Invalid Date",
        'amount': t['amount'],
        'type': t['type'],
        'description': t['description']
    } for t in analyzer.transactions])
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Daily spending chart
    daily_spending = df[df['type'] == 'DEBIT'].groupby('date')['amount'].sum().reset_index()
    fig_daily = px.line(daily_spending, x='date', y='amount',
                        title=translate("Daily Spending Trend", analyzer.language),
                        labels={'amount': translate("Amount", analyzer.language), 'date': translate("Date", analyzer.language)})

    # Top merchants chart
    merchant_data = pd.DataFrame(analyzer.get_merchant_analysis(),
                                 columns=[translate('Merchant', analyzer.language), translate('Amount', analyzer.language)])
    fig_merchants = px.bar(merchant_data.head(10), x=translate('Merchant', analyzer.language), y=translate('Amount', analyzer.language),
                           title=translate("Top 10 Merchants by Spending", analyzer.language))
    fig_merchants.update_layout(xaxis_tickangle=-45)

    fig_pie = px.pie(df, values='amount', names='type',
                     title=translate("Transaction Distribution", analyzer.language))

    return fig_daily, fig_merchants, fig_pie

def translate(text, language):
    translations = {
        'Daily Spending Trend': {'en': 'Daily Spending Trend', 'hi': 'दैनिक खर्च प्रवृत्ति', 'mr': 'दैनंदिन खर्च प्रवृत्ती'},
        'Amount': {'en': 'Amount', 'hi': 'राशि', 'mr': 'रक्कम'},
        'Date': {'en': 'Date', 'hi': 'तारीख', 'mr': 'तारीख'},
        'Merchant': {'en': 'Merchant', 'hi': 'व्यापारी', 'mr': 'व्यापारी'},
        'Top 10 Merchants by Spending': {'en': 'Top 10 Merchants by Spending', 'hi': 'खर्च के अनुसार शीर्ष 10 व्यापारी', 'mr': 'खर्चानुसार शीर्ष १० व्यापारी'},
        'Transaction Distribution': {'en': 'Transaction Distribution', 'hi': 'लेनदेन वितरण', 'mr': 'व्यवहार वितरण'},
        'Total Spending': {'en': 'Total Spending', 'hi': 'कुल खर्च', 'mr': 'एकूण खर्च'},
        'Total Income': {'en': 'Total Income', 'hi': 'कुल आय', 'mr': 'एकूण उत्पन्न'},
        'Net Balance': {'en': 'Net Balance', 'hi': 'कुल शेष', 'mr': 'निव्वळ शिल्लक'},
        'Analysis Period': {'en': 'Analysis Period', 'hi': 'विश्लेषण अवधि', 'mr': 'विश्लेषण कालावधी'},
        'Date Range': {'en': 'Date Range', 'hi': 'तारीख सीमा', 'mr': 'तारीख श्रेणी'},
        'Start Date': {'en': 'Start Date', 'hi': 'प्रारंभ तिथि', 'mr': 'सुरुवात तारीख'},
        'End Date': {'en': 'End Date', 'hi': 'अंतिम तिथि', 'mr': 'शेवटची तारीख'}
    }
    return translations.get(text, {}).get(language, text)

def main_app():
    """Main application after user is logged in."""
    st.title("📊 Transaction Analyzer")
    
    # Create two rows of columns for language and date filters
    # Language selection row
    st.write("Select Language:")
    lang_col1, lang_col2, lang_col3, *spacing = st.columns([1, 1, 1, 2, 2])
    
    if lang_col1.button('English', use_container_width=True):
        selected_language = 'en'
    elif lang_col2.button('हिन्दी', use_container_width=True):
        selected_language = 'hi'
    elif lang_col3.button('मराठी', use_container_width=True):
        selected_language = 'mr'
    else:
        selected_language = 'en'

    st.write("---")  # Add a separator line
    
    uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.read())
            pdf_path = tmp_file.name

        analyzer = TransactionAnalyzer(pdf_path, language=selected_language)
        if not analyzer.transactions:
            st.warning("No transactions were extracted. Please check the PDF format.")
            return

        # Date filter row with a better layout
        st.subheader(translate("Date Range", selected_language))
        date_col1, date_col2, *remaining_cols = st.columns([2, 2, 1, 1])
        
        if analyzer.transactions:
            min_date = min(t['date'] for t in analyzer.transactions)
            max_date = max(t['date'] for t in analyzer.transactions)
            
            # Add date filters in the main content area
            with date_col1:
                start_date = st.date_input(
                    translate("Start Date", selected_language),
                    min_date,
                    min_value=min_date,
                    max_value=max_date,
                    format="YYYY-MM-DD"
                )
            
            with date_col2:
                end_date = st.date_input(
                    translate("End Date", selected_language),
                    max_date,
                    min_value=min_date,
                    max_value=max_date,
                    format="YYYY-MM-DD"
                )

            # Convert date_input to datetime
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Apply date filter
            analyzer.filter_by_date(start_datetime, end_datetime)

            # Add a small info text about the selected date range
            st.caption(f"Showing transactions from {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}")
        
        st.write("---")  # Add a separator line

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs([
            translate("📈 Overview", selected_language), 
            translate("💰 Transactions", selected_language), 
            translate("📊 Charts", selected_language)
        ])

        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    translate("Total Spending", selected_language), 
                    f"₹{analyzer.get_total_spending():,.2f}"
                )
            with col2:
                st.metric(
                    translate("Total Income", selected_language), 
                    f"₹{analyzer.get_total_income():,.2f}"
                )
            with col3:
                st.metric(
                    translate("Net Balance", selected_language), 
                    f"₹{analyzer.get_balance():,.2f}"
                )

        with tab2:
            if analyzer.filtered_transactions:
                transactions_df = pd.DataFrame([{
                    translate('Date', selected_language): t['date'].strftime('%Y-%m-%d'),
                    translate('Description', selected_language): t['description'],
                    translate('Type', selected_language): t['type'],
                    translate('Amount', selected_language): f"₹{t['amount']:,.2f}"
                } for t in analyzer.filtered_transactions])

                st.dataframe(
                    transactions_df, 
                    use_container_width=True,
                    hide_index=True
                )

                # Download buttons in columns for better layout
                dl_col1, dl_col2, *spacing = st.columns([2, 2, 4])
                
                csv = transactions_df.to_csv(index=False).encode('utf-8')
                with dl_col1:
                    st.download_button(
                        translate("Download CSV", selected_language),
                        csv,
                        "transactions.csv",
                        "text/csv",
                        key='download-csv',
                        use_container_width=True
                    )
                
                txt = transactions_df.to_string(index=False)
                with dl_col2:
                    st.download_button(
                        translate("Download TXT", selected_language),
                        txt,
                        "transactions.txt",
                        "text/plain",
                        use_container_width=True
                    )

        with tab3:
            if analyzer.filtered_transactions:
                fig_daily, fig_merchants, fig_pie = create_charts(analyzer)
                st.plotly_chart(fig_daily, use_container_width=True)
                st.plotly_chart(fig_merchants, use_container_width=True)
                col1, col2 = st.columns([2, 1])
                with col2:
                    st.plotly_chart(fig_pie, use_container_width=True)

        os.unlink(pdf_path)

def main():
    """Main function to control the app flow with login."""
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""

    if not st.session_state['logged_in']:
        login()
    else:
        st.sidebar.title("Menu")
        st.sidebar.write(f"Logged in as: {st.session_state['username']}")
        if st.sidebar.button("Logout"):
            logout()
        else:
            main_app()

if __name__ == "__main__":
    main()
