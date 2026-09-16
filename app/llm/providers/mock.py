import json
import re

from app.llm.provider import LLMProvider

_QUESTION_PATTERN = re.compile(r"Question:\s*(.+)", re.IGNORECASE)
_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


def _extract_question(prompt: str) -> str:
    match = _QUESTION_PATTERN.search(prompt)
    return (match.group(1) if match else prompt).strip().lower()


def _extract_number(q: str, default: str) -> str:
    match = _NUMBER_PATTERN.search(q)
    return match.group(0) if match else default


class MockLLMProvider(LLMProvider):
    """Deterministic SQL Server query generator for known business question patterns.

    Used when no LLM_API_KEY is configured so the pipeline and tests never require a live model.
    """

    def generate(self, prompt: str) -> str:
        q = _extract_question(prompt)

        if "top" in q and "customer" in q and "revenue" in q:
            return (
                "SELECT TOP 10 c.CustomerID, c.FirstName, c.LastName, SUM(o.TotalAmount) AS Revenue "
                "FROM customer.Customers c "
                "JOIN sales.Orders o ON o.CustomerID = c.CustomerID "
                "WHERE o.OrderStatus <> 'Cancelled' "
                "GROUP BY c.CustomerID, c.FirstName, c.LastName "
                "ORDER BY Revenue DESC"
            )
        if "top" in q and "product" in q and "revenue" in q:
            return (
                "SELECT TOP 10 p.ProductID, p.ProductName, SUM(oi.LineTotal) AS Revenue "
                "FROM catalog.Products p "
                "JOIN sales.OrderItems oi ON oi.ProductID = p.ProductID "
                "JOIN sales.Orders o ON o.OrderID = oi.OrderID "
                "WHERE o.OrderStatus <> 'Cancelled' "
                "GROUP BY p.ProductID, p.ProductName "
                "ORDER BY Revenue DESC"
            )
        if "monthly" in q and "revenue" in q:
            return (
                "SELECT YEAR(o.OrderDate) AS OrderYear, MONTH(o.OrderDate) AS OrderMonth, "
                "SUM(o.TotalAmount) AS Revenue "
                "FROM sales.Orders o "
                "WHERE o.OrderStatus <> 'Cancelled' "
                "GROUP BY YEAR(o.OrderDate), MONTH(o.OrderDate) "
                "ORDER BY OrderYear, OrderMonth"
            )
        if "return" in q and "rate" in q and "categor" in q:
            return (
                "SELECT cat.CategoryName, "
                "COUNT(DISTINCT r.ReturnID) AS ReturnCount, "
                "COUNT(DISTINCT o.OrderID) AS OrderCount "
                "FROM catalog.Categories cat "
                "JOIN catalog.Products p ON p.CategoryID = cat.CategoryID "
                "JOIN sales.OrderItems oi ON oi.ProductID = p.ProductID "
                "JOIN sales.Orders o ON o.OrderID = oi.OrderID "
                "LEFT JOIN sales.Returns r ON r.OrderID = o.OrderID "
                "GROUP BY cat.CategoryName"
            )
        if "employee" in q and ("target" in q or "performance" in q):
            return (
                "SELECT e.EmployeeID, e.EmployeeName, t.TargetAmount, t.AchievedAmount "
                "FROM hr.Employees e "
                "JOIN sales.SalesTargets t ON t.EmployeeID = e.EmployeeID "
                "WHERE t.AchievedAmount < t.TargetAmount"
            )
        if "inventory" in q and ("reorder" in q or "below" in q or "threshold" in q):
            return (
                "SELECT p.ProductID, p.ProductName, i.WarehouseID, i.QuantityOnHand, i.ReorderLevel "
                "FROM inventory.Inventory i "
                "JOIN catalog.Products p ON p.ProductID = i.ProductID "
                "WHERE i.QuantityOnHand <= i.ReorderLevel"
            )
        if "customer" in q and ("no order" in q or "without order" in q):
            return (
                "SELECT c.CustomerID, c.FirstName, c.LastName "
                "FROM customer.Customers c "
                "LEFT JOIN sales.Orders o ON o.CustomerID = c.CustomerID "
                "WHERE o.OrderID IS NULL"
            )
        if "late" in q and "shipment" in q:
            return (
                "SELECT s.ShipmentID, s.OrderID, s.ExpectedDate, s.DeliveredDate "
                "FROM sales.Shipments s "
                "WHERE s.DeliveredDate > s.ExpectedDate"
            )
        if "campaign" in q and "revenue" in q:
            return (
                "SELECT c.CampaignName, SUM(cr.RevenueGenerated) AS Revenue "
                "FROM marketing.Campaigns c "
                "JOIN marketing.CampaignResponses cr ON cr.CampaignID = c.CampaignID "
                "GROUP BY c.CampaignName "
                "ORDER BY Revenue DESC"
            )
        if ("rank" in q or "ranking" in q) and "customer" in q:
            return (
                "SELECT c.CustomerID, c.FirstName, c.LastName, SUM(o.TotalAmount) AS Revenue, "
                "RANK() OVER (ORDER BY SUM(o.TotalAmount) DESC) AS RevenueRank "
                "FROM customer.Customers c "
                "JOIN sales.Orders o ON o.CustomerID = c.CustomerID "
                "WHERE o.OrderStatus <> 'Cancelled' "
                "GROUP BY c.CustomerID, c.FirstName, c.LastName"
            )
        if ("rank" in q or "ranking" in q) and "product" in q:
            return (
                "SELECT p.ProductID, p.ProductName, SUM(oi.LineTotal) AS Revenue, "
                "RANK() OVER (ORDER BY SUM(oi.LineTotal) DESC) AS RevenueRank "
                "FROM catalog.Products p "
                "JOIN sales.OrderItems oi ON oi.ProductID = p.ProductID "
                "GROUP BY p.ProductID, p.ProductName"
            )
        if "running total" in q:
            return (
                "SELECT CAST(o.OrderDate AS DATE) AS OrderDay, SUM(o.TotalAmount) AS DailyRevenue, "
                "SUM(SUM(o.TotalAmount)) OVER (ORDER BY CAST(o.OrderDate AS DATE)) AS RunningTotal "
                "FROM sales.Orders o "
                "WHERE o.OrderStatus <> 'Cancelled' "
                "GROUP BY CAST(o.OrderDate AS DATE) "
                "ORDER BY OrderDay"
            )
        if ("percentage" in q or "percent" in q or "share" in q) and "revenue" in q:
            return (
                "SELECT cat.CategoryName, SUM(oi.LineTotal) AS Revenue, "
                "ROUND(100.0 * SUM(oi.LineTotal) / SUM(SUM(oi.LineTotal)) OVER (), 2) AS RevenueSharePct "
                "FROM catalog.Categories cat "
                "JOIN catalog.Products p ON p.CategoryID = cat.CategoryID "
                "JOIN sales.OrderItems oi ON oi.ProductID = p.ProductID "
                "GROUP BY cat.CategoryName"
            )
        if "cohort" in q or ("customer" in q and "signup" in q):
            return (
                "SELECT YEAR(c.SignupDate) AS SignupYear, MONTH(c.SignupDate) AS SignupMonth, "
                "COUNT(DISTINCT c.CustomerID) AS Cohort, SUM(o.TotalAmount) AS CohortRevenue "
                "FROM customer.Customers c "
                "JOIN sales.Orders o ON o.CustomerID = c.CustomerID "
                "GROUP BY YEAR(c.SignupDate), MONTH(c.SignupDate) "
                "ORDER BY SignupYear, SignupMonth"
            )
        if "customer" in q and "more than" in q and "order" in q:
            threshold = _extract_number(q, "10")
            return (
                "SELECT c.CustomerID, c.FirstName, c.LastName, COUNT(o.OrderID) AS OrderCount "
                "FROM customer.Customers c "
                "JOIN sales.Orders o ON o.CustomerID = c.CustomerID "
                "GROUP BY c.CustomerID, c.FirstName, c.LastName "
                f"HAVING COUNT(o.OrderID) > {threshold}"
            )
        if "rating" in q and ("above" in q or "over" in q):
            threshold = _extract_number(q, "4")
            return (
                "SELECT p.ProductID, p.ProductName, AVG(CAST(r.Rating AS FLOAT)) AS AverageRating "
                "FROM catalog.Products p "
                "JOIN catalog.ProductReviews r ON r.ProductID = p.ProductID "
                "GROUP BY p.ProductID, p.ProductName "
                f"HAVING AVG(CAST(r.Rating AS FLOAT)) > {threshold}"
            )
        if "revenue" in q and ("region" in q or "state" in q):
            return (
                "SELECT o.ShippingState, SUM(o.TotalAmount) AS Revenue "
                "FROM sales.Orders o "
                "WHERE o.OrderStatus <> 'Cancelled' "
                "GROUP BY o.ShippingState "
                "ORDER BY Revenue DESC"
            )
        if "inventory" in q and "value" in q and "warehouse" in q:
            return (
                "SELECT i.WarehouseID, SUM(i.QuantityOnHand * p.UnitCost) AS InventoryValue "
                "FROM inventory.Inventory i "
                "JOIN catalog.Products p ON p.ProductID = i.ProductID "
                "GROUP BY i.WarehouseID "
                "ORDER BY InventoryValue DESC"
            )
        if "average order" in q or "aov" in q:
            return (
                "SELECT ROUND(SUM(o.TotalAmount) / COUNT(DISTINCT o.OrderID), 2) AS AverageOrderValue "
                "FROM sales.Orders o "
                "WHERE o.OrderStatus <> 'Cancelled'"
            )
        if "revenue" in q or "total sales" in q:
            return "SELECT SUM(o.TotalAmount) AS Revenue FROM sales.Orders o WHERE o.OrderStatus <> 'Cancelled'"

        raise ValueError("The question is ambiguous. Please specify a business metric, table, or dimension.")

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        return json.loads(self.generate(prompt))
