from typing import List, Dict, Optional
from dataclasses import dataclass
from decimal import Decimal
import logging

@dataclass
class GridConfig:
    """网格交易配置类"""
    symbol: str                # 交易对
    upper_price: float         # 网格上限价格
    lower_price: float         # 网格下限价格
    grid_number: int           # 网格数量
    total_invest: float        # 总投资额
    price_precision: int = 8   # 价格精度
    size_precision: int = 8    # 数量精度

    def __post_init__(self):
        if self.upper_price <= self.lower_price:
            raise ValueError("上限价格必须大于下限价格")
        if self.grid_number <= 0:
            raise ValueError("网格数量必须大于0")
        if self.total_invest <= 0:
            raise ValueError("总投资额必须大于0")

class GridTrading:
    """网格交易策略实现类"""
    def __init__(self, config: GridConfig):
        self.config = config
        self.grid_profit = (config.upper_price - config.lower_price) / config.grid_number
        self.grid_prices = self._calculate_grid_prices()
        self.grid_amounts = self._calculate_grid_amounts()
        self.orders: Dict[str, Dict] = {}  # 订单管理
        self.position = 0.0                # 当前持仓
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("GridTrading")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _calculate_grid_prices(self) -> List[float]:
        """计算网格价格列表"""
        prices = []
        for i in range(self.config.grid_number + 1):
            price = self.config.lower_price + i * self.grid_profit
            price = round(price, self.config.price_precision)
            prices.append(price)
        return prices

    def _calculate_grid_amounts(self) -> List[float]:
        """计算每个网格的交易数量"""
        grid_invest = self.config.total_invest / self.config.grid_number
        amounts = []
        for price in self.grid_prices[:-1]:  # 最后一个价格不需要计算数量
            amount = grid_invest / price
            amount = round(amount, self.config.size_precision)
            amounts.append(amount)
        return amounts

    def place_grid_orders(self, current_price: float) -> None:
        """根据当前价格放置网格订单"""
        try:
            # 找到当前价格所在的网格
            current_grid = None
            for i in range(len(self.grid_prices) - 1):
                if self.grid_prices[i] <= current_price < self.grid_prices[i + 1]:
                    current_grid = i
                    break

            if current_grid is None:
                self.logger.warning(f"当前价格 {current_price} 不在网格范围内")
                return

            # 放置买单
            for i in range(current_grid):
                self._place_buy_order(self.grid_prices[i], self.grid_amounts[i])

            # 放置卖单
            for i in range(current_grid + 1, len(self.grid_prices) - 1):
                self._place_sell_order(self.grid_prices[i], self.grid_amounts[i-1])

        except Exception as e:
            self.logger.error(f"放置网格订单失败: {str(e)}")

    def _place_buy_order(self, price: float, amount: float) -> None:
        """放置买单"""
        order_id = f"buy_{price}"
        order = {
            "type": "buy",
            "price": price,
            "amount": amount,
            "status": "pending"
        }
        self.orders[order_id] = order
        self.logger.info(f"放置买单: 价格={price}, 数量={amount}")

    def _place_sell_order(self, price: float, amount: float) -> None:
        """放置卖单"""
        order_id = f"sell_{price}"
        order = {
            "type": "sell",
            "price": price,
            "amount": amount,
            "status": "pending"
        }
        self.orders[order_id] = order
        self.logger.info(f"放置卖单: 价格={price}, 数量={amount}")

    def handle_order_filled(self, order_id: str) -> None:
        """处理订单成交"""
        if order_id not in self.orders:
            self.logger.warning(f"未找到订单: {order_id}")
            return

        order = self.orders[order_id]
        if order["type"] == "buy":
            self.position += order["amount"]
            # 在买单成交价格上方放置卖单
            self._place_sell_order(order["price"] + self.grid_profit, order["amount"])
        else:  # sell
            self.position -= order["amount"]
            # 在卖单成交价格下方放置买单
            self._place_buy_order(order["price"] - self.grid_profit, order["amount"])

        order["status"] = "filled"
        self.logger.info(f"订单成交: {order_id}, 当前持仓: {self.position}")

    def cancel_all_orders(self) -> None:
        """取消所有未成交订单"""
        for order_id, order in self.orders.items():
            if order["status"] == "pending":
                order["status"] = "cancelled"
                self.logger.info(f"取消订单: {order_id}")

    def get_grid_status(self) -> Dict:
        """获取网格状态"""
        return {
            "symbol": self.config.symbol,
            "grid_profit": self.grid_profit,
            "position": self.position,
            "orders": self.orders
        }