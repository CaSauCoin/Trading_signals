import logging
import os
from groq import Groq
import google.generativeai as genai
from duckduckgo_search import DDGS

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not found in environment variables! Please create .env file.")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables! Please create .env file.")

class TradingCouncil:
    def __init__(self):
        self.is_ready = False
        try:
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            self.logic_model = "llama-3.3-70b-versatile"

            genai.configure(api_key=GEMINI_API_KEY)
            self.news_model = genai.GenerativeModel('gemini-2.5-flash')
            self.is_ready = True
            logger.info(f"✅ AI Council Ready: Logic=[{self.logic_model}] | News=[Gemini Flash]")
        except Exception as e:
            logger.error(f"❌ Init AI Council Failed: {e}")

    # --- AGENT 1: (TECHNICAL ANALYST) ---
    def _run_technical_agent(self, symbol, timeframe, smc_data, indicators):
        """
        AI chỉ nhìn vào số liệu SMC và Indicators để đưa ra nhận định chart.
        """
        # Trích xuất dữ liệu để prompt ngắn gọn hơn
        price = indicators.get('current_price', 0)
        rsi = indicators.get('rsi', 50)
        ema = indicators.get('ema_20', 0)

        bos_list = smc_data.get('break_of_structure', [])
        last_bos = bos_list[-1]['type'] if bos_list else "None"

        ob_list = smc_data.get('order_blocks', [])
        last_ob = "None"
        if ob_list:
            ob = ob_list[-1]
            last_ob = f"{ob['type']} ({ob['high']} - {ob['low']})"

        fvg_list = smc_data.get('fair_value_gaps', [])
        last_fvg = fvgs = f"{fvg_list[-1]['type']}" if fvg_list else "None"

        prompt = f"""
        Role: Senior Technical Analyst specialized in Smart Money Concepts (SMC).
        Task: Analyze the market structure for {symbol} ({timeframe}).

        MARKET DATA:
        - Price: {price}
        - Trend (EMA20): {ema}
        - RSI (14): {rsi:.2f}

        SMC STRUCTURE:
        - Latest BOS: {last_bos}
        - Nearest Order Block: {last_ob}
        - Nearest FVG: {last_fvg}

        INSTRUCTIONS:
        1. Determine the bias (Bullish/Bearish/Neutral) based strictly on Market Structure.
        2. Identify if price is reacting to an Order Block or Liquidity Zone.
        3. Keep the output concise and professional.
        """

        try:
            completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.logic_model,
                temperature=0.3,  # Thấp để đảm bảo tính logic, ít "chém gió"
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Tech Agent Error: {e}")
            return "Technical analysis unavailable due to AI error."

    # --- AGENT 2: (NEWS REPORTER) ---
    def _run_news_agent(self, symbol):
        """
        Search Google/DuckDuckGo và dùng Gemini tóm tắt sentiment.
        """
        try:
            # 1. Tạo query search thông minh
            clean_symbol = symbol.replace("/USDT", "").replace("USD", "")
            query = f"{clean_symbol} crypto price news analysis today"
            if "XAU" in clean_symbol or "GOLD" in clean_symbol:
                query = "Gold price market news analysis today"

            # 2. Search (Lấy 5 kết quả mới nhất)
            # DDGS chạy free, không cần API Key
            results = DDGS().text(keywords=query, max_results=5)

            if not results:
                return "No significant news found today."

            # Ghép nội dung tin tức lại
            news_context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])

            # 3. Hỏi Gemini
            prompt = f"""
            Role: Crypto Market News Reporter.
            Task: Summarize the market sentiment for **{symbol}** based on the news below.

            RAW NEWS DATA:
            {news_context}

            INSTRUCTIONS:
            1. What is the general sentiment? (Positive/Negative/Neutral/Uncertain).
            2. List 1-2 key events driving the price (e.g., SEC, War, Inflation, Whale movement).
            3. Keep it short (under 50 words).
            """

            response = self.news_model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"News Agent Error: {e}")
            return "News service unavailable (Connection error)."

    # --- AGENT 3: (CHIEF STRATEGIST) ---
    def execute_analysis_pipeline(self, symbol, timeframe, smc_data, indicators, setup_params):
        """
        Sếp Tổng ra quyết định + Chọn kèo (Setup) cụ thể.
        """
        if not self.is_ready:
            return "⚠️ AI System not ready."

        logger.info(f"🧠 AI Council meeting for {symbol}...")

        # 1. Lấy báo cáo từ đệ tử
        tech_report = self._run_technical_agent(symbol, timeframe, smc_data, indicators)
        news_report = self._run_news_agent(symbol)

        # 2. Sếp tổng họp
        # Nhét 2 kịch bản giá đã tính toán vào prompt
        final_prompt = f"""
        Role: Head of Trading Strategy.
        Task: Synthesize reports and provide a FINAL trade decision with EXACT NUMBERS for {symbol} ({timeframe}).

        --- INPUT DATA ---
        1. TECH REPORT: {tech_report}
        2. NEWS REPORT: {news_report}

        --- CALCULATED SETUPS (USE THESE NUMBERS) ---
        If BULLISH, use this: [ {setup_params['long_setup']} ]
        If BEARISH, use this: [ {setup_params['short_setup']} ]

        --- INSTRUCTIONS ---
        1. Decide ACTION: BUY, SELL, or WAIT based on confluence of Tech & News.
        2. If BUY/SELL: You MUST copy the corresponding "Calculated Setup" numbers above into your conclusion. Do NOT invent new numbers.
        3. If WAIT: Do not provide entry numbers.

        --- OUTPUT FORMAT (Telegram Markdown) ---

        ### 🧠 HỘI ĐỒNG AI QUYẾT NGHỊ

        **1. 📉 Kỹ thuật:** [Summary 1 sentence]
        **2. 📰 Tin tức:** [Summary 1 sentence]

        **3. ⚖️ KẾT LUẬN:**
        👉 **ACTION:** [BUY / SELL / WAIT]
        🔥 **Confidence:** [0-10]/10

        🎯 **CHIẾN LƯỢC ĐỀ XUẤT:**
        *(Chỉ hiển thị nếu Action là BUY/SELL)*
        • **Entry:** ...
        • **Stoploss:** ...
        • **Take Profit:** ...

        📝 **Lý do:** [Ngắn gọn]
        """

        try:
            completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": final_prompt}],
                model=self.logic_model,
                temperature=0.5  # Đủ thấp để nó tuân thủ số liệu
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Chief Agent Error: {e}")
            return "⚠️ AI System Error."