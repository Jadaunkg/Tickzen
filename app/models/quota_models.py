"""
Quota Data Models
Represents quota-related data structures for Firestore
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class PlanType(Enum):
    """Subscription plan types"""
    FREE = "free"
    PRO = "pro"
    PRO_PLUS = "pro_plus"
    ENTERPRISE = "enterprise"


class ResourceType(Enum):
    """Types of resources that can be quota-limited"""
    STOCK_REPORT = "stock_report"


class UsageStatus(Enum):
    """Status of a usage entry"""
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class QuotaLimits:
    """Quota limits for a user or plan"""
    stock_reports_monthly: int = 10
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'QuotaLimits':
        """Create from dictionary"""
        return cls(
            stock_reports_monthly=data.get('stock_reports_monthly', 10)
        )


@dataclass
class CurrentUsage:
    """Current usage counters"""
    stock_reports: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'CurrentUsage':
        """Create from dictionary"""
        return cls(
            stock_reports=data.get('stock_reports', 0)
        )
    
    def reset(self):
        """Reset all counters to zero"""
        self.stock_reports = 0


@dataclass
class LifetimeStats:
    """Lifetime statistics for a user"""
    total_stock_reports: int = 0
    member_since: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_stock_reports': self.total_stock_reports,
            'member_since': self.member_since
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LifetimeStats':
        """Create from dictionary"""
        return cls(
            total_stock_reports=data.get('total_stock_reports', 0),
            member_since=data.get('member_since', datetime.now(timezone.utc))
        )


@dataclass
class UserQuota:
    """Main user quota document"""
    user_uid: str
    plan_type: str = "free"
    plan_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    quota_limits: QuotaLimits = field(default_factory=QuotaLimits)
    current_usage: CurrentUsage = field(default_factory=CurrentUsage)
    
    current_period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    is_suspended: bool = False
    suspension_reason: Optional[str] = None
    
    lifetime_stats: LifetimeStats = field(default_factory=LifetimeStats)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        return {
            'user_uid': self.user_uid,
            'plan_type': self.plan_type,
            'plan_updated_at': self.plan_updated_at,
            'quota_limits': self.quota_limits.to_dict(),
            'current_usage': self.current_usage.to_dict(),
            'current_period_start': self.current_period_start,
            'current_period_end': self.current_period_end,
            'last_reset': self.last_reset,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_suspended': self.is_suspended,
            'suspension_reason': self.suspension_reason,
            'lifetime_stats': self.lifetime_stats.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserQuota':
        """Create from Firestore document"""
        return cls(
            user_uid=data['user_uid'],
            plan_type=data.get('plan_type', 'free'),
            plan_updated_at=data.get('plan_updated_at', datetime.now(timezone.utc)),
            quota_limits=QuotaLimits.from_dict(data.get('quota_limits', {})),
            current_usage=CurrentUsage.from_dict(data.get('current_usage', {})),
            current_period_start=data.get('current_period_start', datetime.now(timezone.utc)),
            current_period_end=data.get('current_period_end', datetime.now(timezone.utc)),
            last_reset=data.get('last_reset', datetime.now(timezone.utc)),
            created_at=data.get('created_at', datetime.now(timezone.utc)),
            updated_at=data.get('updated_at', datetime.now(timezone.utc)),
            is_suspended=data.get('is_suspended', False),
            suspension_reason=data.get('suspension_reason'),
            lifetime_stats=LifetimeStats.from_dict(data.get('lifetime_stats', {}))
        )


@dataclass
class StockReportUsage:
    """Individual stock report usage record"""
    ticker: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    report_id: Optional[str] = None
    status: str = "success"
    generation_time_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp,
            'report_id': self.report_id,
            'status': self.status,
            'generation_time_ms': self.generation_time_ms
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockReportUsage':
        """Create from dictionary"""
        return cls(
            ticker=data['ticker'],
            timestamp=data.get('timestamp', datetime.now(timezone.utc)),
            report_id=data.get('report_id'),
            status=data.get('status', 'success'),
            generation_time_ms=data.get('generation_time_ms', 0)
        )


@dataclass
class DailyStats:
    """Daily usage statistics"""
    stock_reports: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'DailyStats':
        """Create from dictionary"""
        return cls(
            stock_reports=data.get('stock_reports', 0)
        )


@dataclass
class MonthlySummary:
    """Monthly usage summary"""
    total_stock_reports: int = 0
    peak_usage_day: Optional[str] = None
    avg_daily_usage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonthlySummary':
        """Create from dictionary"""
        return cls(
            total_stock_reports=data.get('total_stock_reports', 0),
            peak_usage_day=data.get('peak_usage_day'),
            avg_daily_usage=data.get('avg_daily_usage', 0.0)
        )


@dataclass
class UsageHistory:
    """Usage history document (monthly)"""
    period: str  # "YYYY-MM" format
    user_uid: str
    
    stock_reports: List[Dict[str, Any]] = field(default_factory=list)
    
    daily_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    summary: MonthlySummary = field(default_factory=MonthlySummary)
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        return {
            'period': self.period,
            'user_uid': self.user_uid,
            'stock_reports': self.stock_reports,
            'daily_stats': self.daily_stats,
            'summary': self.summary.to_dict(),
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UsageHistory':
        """Create from Firestore document"""
        return cls(
            period=data['period'],
            user_uid=data['user_uid'],
            stock_reports=data.get('stock_reports', []),
            daily_stats=data.get('daily_stats', {}),
            summary=MonthlySummary.from_dict(data.get('summary', {})),
            created_at=data.get('created_at', datetime.now(timezone.utc)),
            updated_at=data.get('updated_at', datetime.now(timezone.utc))
        )
    
    def add_stock_report(self, usage: StockReportUsage):
        """Add a stock report usage entry"""
        self.stock_reports.append(usage.to_dict())
        
        # Update daily stats
        date_key = usage.timestamp.strftime('%Y-%m-%d')
        if date_key not in self.daily_stats:
            self.daily_stats[date_key] = {'stock_reports': 0}
        self.daily_stats[date_key]['stock_reports'] += 1
        
        # Update summary
        self.summary.total_stock_reports += 1
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class QuotaPlan:
    """Quota plan configuration"""
    plan_id: str
    display_name: str
    limits: QuotaLimits
    features: List[str]
    price_monthly: float
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        return {
            'plan_id': self.plan_id,
            'display_name': self.display_name,
            'limits': self.limits.to_dict(),
            'features': self.features,
            'price_monthly': self.price_monthly,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuotaPlan':
        """Create from Firestore document"""
        return cls(
            plan_id=data['plan_id'],
            display_name=data['display_name'],
            limits=QuotaLimits.from_dict(data.get('limits', {})),
            features=data.get('features', []),
            price_monthly=data.get('price_monthly', 0.0),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at', datetime.now(timezone.utc)),
            updated_at=data.get('updated_at', datetime.now(timezone.utc))
        )
