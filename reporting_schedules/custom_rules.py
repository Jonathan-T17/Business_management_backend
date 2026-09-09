class CustomScheduleRuleEngine:
    """Small safe rule engine. No eval(), Python code, or arbitrary expressions."""

    @classmethod
    def applies(cls, rule, target_date):
        rule = rule or {}
        kind = rule.get("type")
        if kind == "WEEKDAYS":
            return target_date.weekday() in set(rule.get("days", []))
        if kind == "DAY_INTERVAL":
            from datetime import date
            start = date.fromisoformat(rule["start_date"])
            interval = int(rule.get("interval", 1))
            return interval > 0 and (target_date - start).days >= 0 and (target_date - start).days % interval == 0
        return False
