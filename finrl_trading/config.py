"""Configuration module for FinRL-Trading.

Loads and validates environment variables and provides
centralized configuration for the trading system.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DataConfig:
    """Configuration for market data sources."""
    start_date: str = os.getenv("DATA_START_DATE", "2018-01-01")
    end_date: str = os.getenv("DATA_END_DATE", "2023-12-31")
    ticker_list: List[str] = field(default_factory=lambda: [
        ticker.strip()
        for ticker in os.getenv(
            "TICKER_LIST",
            "AAPL,MSFT,GOOGL,AMZN,TSLA,META,NVDA,JPM,V,JNJ"
        ).split(",")
    ])
    data_source: str = os.getenv("DATA_SOURCE", "yahoofinance")
    time_interval: str = os.getenv("TIME_INTERVAL", "1D")


@dataclass
class EnvConfig:
    """Configuration for the RL trading environment."""
    initial_amount: float = float(os.getenv("INITIAL_AMOUNT", "1000000"))
    transaction_cost_pct: float = float(os.getenv("TRANSACTION_COST_PCT", "0.001"))
    reward_scaling: float = float(os.getenv("REWARD_SCALING", "1e-4"))
    max_stock_quantity: int = int(os.getenv("MAX_STOCK_QUANTITY", "100"))
    turbulence_threshold: Optional[float] = (
        float(os.getenv("TURBULENCE_THRESHOLD"))
        if os.getenv("TURBULENCE_THRESHOLD")
        else None
    )
    tech_indicators: List[str] = field(default_factory=lambda: [
        "macd", "boll_ub", "boll_lb", "rsi_30",
        "cci_30", "dx_30", "close_30_sma", "close_60_sma"
    ])


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    agent: str = os.getenv("RL_AGENT", "ppo")
    total_timesteps: int = int(os.getenv("TOTAL_TIMESTEPS", "500000"))
    learning_rate: float = float(os.getenv("LEARNING_RATE", "3e-4"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "2048"))
    n_epochs: int = int(os.getenv("N_EPOCHS", "10"))
    seed: int = int(os.getenv("RANDOM_SEED", "42"))
    trained_model_dir: str = os.getenv("TRAINED_MODEL_DIR", "trained_models")
    tensorboard_log_dir: str = os.getenv("TENSORBOARD_LOG_DIR", "tensorboard_log")


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    backtest_start_date: str = os.getenv("BACKTEST_START_DATE", "2023-01-01")
    backtest_end_date: str = os.getenv("BACKTEST_END_DATE", "2023-12-31")
    baseline_ticker: str = os.getenv("BASELINE_TICKER", "^DJI")
    results_dir: str = os.getenv("RESULTS_DIR", "results")


@dataclass
class AppConfig:
    """Top-level application configuration."""
    data: DataConfig = field(default_factory=DataConfig)
    env: EnvConfig = field(default_factory=EnvConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    use_gpu: bool = os.getenv("USE_GPU", "false").lower() == "true"

    def validate(self) -> None:
        """Validate critical configuration values."""
        valid_agents = {"ppo", "a2c", "ddpg", "td3", "sac"}
        if self.training.agent.lower() not in valid_agents:
            raise ValueError(
                f"Invalid RL agent '{self.training.agent}'. "
                f"Choose from: {valid_agents}"
            )
        if self.env.initial_amount <= 0:
            raise ValueError("INITIAL_AMOUNT must be positive.")
        if not (0 <= self.env.transaction_cost_pct < 1):
            raise ValueError("TRANSACTION_COST_PCT must be between 0 and 1.")
        if not self.data.ticker_list:
            raise ValueError("TICKER_LIST must not be empty.")


# Singleton config instance
config = AppConfig()
