"""
Advanced Fund Analysis Ratios & Models — Pure Python Implementation.

Implements academic/industry best practices without numpy/scipy dependencies:
- Classic risk-adjusted returns: Sharpe, Sortino, Treynor, Jensen's Alpha, Information Ratio
- Advanced ratios: Omega, Calmar, Sterling, Burke, Kappa3, Gain-Loss
- Factor models: Fama-French 3-Factor, Carhart 4-Factor (simplified OLS)
- Risk metrics: CVaR/ES, MaxDD, Upside/Downside Capture, Tail Ratio, Pain Index
- Rolling window stability analysis
- Category-relative scoring (Morningstar-style)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from statistics import mean, stdev, median


def _percentile(data: Sequence[float], p: float) -> float:
    """Compute percentile (0-100)."""
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 0:
        return 0.0
    index = (p / 100) * (n - 1)
    if index.is_integer():
        return sorted_data[int(index)]
    lower = sorted_data[int(index)]
    upper = sorted_data[int(index) + 1]
    return lower + (upper - lower) * (index - int(index))


def _covariance(x: Sequence[float], y: Sequence[float]) -> float:
    """Sample covariance."""
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    mx, my = mean(x), mean(y)
    return sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / (len(x) - 1)


def _variance(data: Sequence[float]) -> float:
    """Sample variance."""
    return stdev(data) ** 2 if len(data) > 1 else 0.0


def _correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Pearson correlation."""
    vx, vy = _variance(x), _variance(y)
    if vx == 0 or vy == 0:
        return 0.0
    return _covariance(x, y) / math.sqrt(vx * vy)


def _ols_simple(x: Sequence[float], y: Sequence[float]) -> tuple[float, float, float]:
    """
    Simple OLS regression: y = alpha + beta * x
    Returns: (alpha, beta, r_squared)
    """
    n = len(x)
    if n < 2:
        return 0.0, 0.0, 0.0
    
    mx, my = mean(x), mean(y)
    cov = _covariance(x, y)
    vx = _variance(x)
    
    if vx == 0:
        return my, 0.0, 0.0
    
    beta = cov / vx
    alpha = my - beta * mx
    
    # R-squared
    y_pred = [alpha + beta * xi for xi in x]
    ss_res = sum((yi - ypi) ** 2 for yi, ypi in zip(y, y_pred))
    ss_tot = sum((yi - my) ** 2 for yi in y)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    
    return alpha, beta, max(0.0, r2)


@dataclass
class RiskAdjustedRatios:
    """Container for all risk-adjusted performance ratios."""
    # Classic
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    treynor_ratio: Optional[float] = None
    jensen_alpha: Optional[float] = None
    information_ratio: Optional[float] = None
    
    # Advanced
    omega_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    sterling_ratio: Optional[float] = None
    burke_ratio: Optional[float] = None
    kappa3_ratio: Optional[float] = None
    gain_loss_ratio: Optional[float] = None
    upside_potential_ratio: Optional[float] = None
    
    # Tail risk
    cvar_95: Optional[float] = None
    var_95: Optional[float] = None
    tail_ratio: Optional[float] = None
    pain_index: Optional[float] = None
    max_drawdown: Optional[float] = None
    avg_drawdown: Optional[float] = None
    ulcer_index: Optional[float] = None
    
    # Capture ratios
    upside_capture: Optional[float] = None
    downside_capture: Optional[float] = None
    capture_ratio: Optional[float] = None
    
    # Higher moments
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    
    # Metadata
    n_observations: int = 0
    risk_free_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "treynor_ratio": self.treynor_ratio,
            "jensen_alpha": self.jensen_alpha,
            "information_ratio": self.information_ratio,
            "omega_ratio": self.omega_ratio,
            "calmar_ratio": self.calmar_ratio,
            "sterling_ratio": self.sterling_ratio,
            "burke_ratio": self.burke_ratio,
            "kappa3_ratio": self.kappa3_ratio,
            "gain_loss_ratio": self.gain_loss_ratio,
            "upside_potential_ratio": self.upside_potential_ratio,
            "cvar_95": self.cvar_95,
            "var_95": self.var_95,
            "tail_ratio": self.tail_ratio,
            "pain_index": self.pain_index,
            "max_drawdown": self.max_drawdown,
            "avg_drawdown": self.avg_drawdown,
            "ulcer_index": self.ulcer_index,
            "upside_capture": self.upside_capture,
            "downside_capture": self.downside_capture,
            "capture_ratio": self.capture_ratio,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
            "n_observations": self.n_observations,
            "risk_free_rate": self.risk_free_rate,
        }


@dataclass
class FactorModelResult:
    """Results from factor model regressions."""
    model_name: str
    alpha: float
    alpha_t_stat: Optional[float]
    alpha_p_value: Optional[float]
    betas: dict[str, float]
    beta_t_stats: dict[str, Optional[float]]
    r_squared: float
    adj_r_squared: float
    f_statistic: Optional[float]
    residuals: list[float]
    n_obs: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "model_name": self.model_name,
            "alpha": self.alpha,
            "alpha_t_stat": self.alpha_t_stat,
            "alpha_p_value": self.alpha_p_value,
            "betas": self.betas,
            "beta_t_stats": self.beta_t_stats,
            "r_squared": self.r_squared,
            "adj_r_squared": self.adj_r_squared,
            "f_statistic": self.f_statistic,
            "residuals": self.residuals,
            "n_obs": self.n_obs,
        }


@dataclass
class RollingStability:
    """Rolling window stability metrics."""
    metric_name: str
    rolling_values: list[float]
    mean: float
    std: float
    min_val: float
    max_val: float
    stability_score: float
    trend: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "metric_name": self.metric_name,
            "rolling_values": self.rolling_values,
            "mean": self.mean,
            "std": self.std,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "stability_score": self.stability_score,
            "trend": self.trend,
        }


@dataclass
class CategoryRelativeScore:
    """Morningstar-style category-relative scoring."""
    category: str
    n_peers: int
    percentile_rank: float
    star_rating: int
    category_rank: int
    total_in_category: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "category": self.category,
            "n_peers": self.n_peers,
            "percentile_rank": self.percentile_rank,
            "star_rating": self.star_rating,
            "category_rank": self.category_rank,
            "total_in_category": self.total_in_category,
        }


class AdvancedFundAnalyzer:
    """
    Comprehensive fund analysis based on academic literature:
    - Sharpe (1966), Sortino & Price (1994), Treynor (1965)
    - Jensen (1968), Fama & French (1993, 2015), Carhart (1997)
    - Omega (Keating & Shadwick, 2002), Calmar (Young, 1991)
    - CVaR/ES (Rockafellar & Uryasev, 2000)
    - Upside/Downside Capture (Petersen, 1997)
    - Morningstar Category Ratings methodology
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        min_observations: int = 30,
        rolling_windows: Optional[list[int]] = None,
    ) -> None:
        self.rf_daily = risk_free_rate / 252.0
        self.rf_annual = risk_free_rate
        self.min_obs = min_observations
        self.rolling_windows = rolling_windows or [30, 60, 90, 120, 252]
    
    def analyze(
        self,
        returns: Sequence[float],
        benchmark_returns: Optional[Sequence[float]] = None,
        category_returns: Optional[dict[str, Sequence[float]]] = None,
    ) -> dict[str, Any]:
        """Full analysis pipeline."""
        if len(returns) < self.min_obs:
            return {"error": f"Insufficient data: {len(returns)} < {self.min_obs}"}
        
        results = {}
        
        # 1. Risk-adjusted ratios
        ratios = self._compute_ratios(returns, benchmark_returns)
        results["ratios"] = ratios.to_dict()
        
        # 2. Factor models
        if benchmark_returns is not None and len(benchmark_returns) >= self.min_obs:
            fm = self._run_factor_models(returns, benchmark_returns)
            results["factor_models"] = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in fm.items()}
        
        # 3. Rolling stability
        rs = self._compute_rolling_stability(returns, benchmark_returns)
        results["rolling_stability"] = {k: v.to_dict() for k, v in rs.items()}
        
        # 4. Category-relative
        if category_returns:
            # Wrap single sequence into list of sequences for compatibility
            wrapped = {k: [v] if not isinstance(v, list) or (v and not isinstance(v[0], Sequence)) else v 
                       for k, v in category_returns.items()}
            cr = self._compute_category_relative(returns, wrapped)
            results["category_relative"] = {k: v.to_dict() for k, v in cr.items()}
        
        # 5. Composite score
        results["composite_score"] = self._composite_score(results)
        
        return results
    
    def _compute_ratios(
        self,
        returns: Sequence[float],
        benchmark: Optional[Sequence[float]] = None,
    ) -> RiskAdjustedRatios:
        """Compute all risk-adjusted performance ratios."""
        n = len(returns)
        mean_r = mean(returns)
        std_r = stdev(returns) if n > 1 else 0.0
        
        excess = [r - self.rf_daily for r in returns]
        mean_excess = mean(excess)
        std_excess = stdev(excess) if n > 1 else 0.0
        
        downside = [r for r in excess if r < 0]
        downside_dev = stdev(downside) if len(downside) > 1 else 0.0
        
        ratios = RiskAdjustedRatios(
            n_observations=n,
            risk_free_rate=self.rf_annual,
        )
        
        # Sharpe (annualized)
        if std_excess > 0:
            ratios.sharpe_ratio = mean_excess / std_excess * math.sqrt(252)
        
        # Sortino
        if downside_dev > 0:
            ratios.sortino_ratio = mean_excess / downside_dev * math.sqrt(252)
        
        # Benchmark-dependent ratios
        if benchmark is not None and len(benchmark) == n:
            beta = self._compute_beta(returns, benchmark)
            if beta > 0:
                ratios.treynor_ratio = mean_excess / beta * 252
            
            bench_mean = mean(benchmark)
            ratios.jensen_alpha = (mean_r - self.rf_daily) - beta * (bench_mean - self.rf_daily)
            ratios.jensen_alpha *= 252
            
            # Information Ratio
            active_returns = [r - b for r, b in zip(returns, benchmark)]
            active_mean = mean(active_returns)
            active_std = stdev(active_returns) if n > 1 else 0.0
            if active_std > 0:
                ratios.information_ratio = active_mean / active_std * math.sqrt(252)
            
            # Capture Ratios
            up_market = [b > 0 for b in benchmark]
            down_market = [b < 0 for b in benchmark]
            if any(up_market) and any(down_market):
                up_fund = [r for r, u in zip(returns, up_market) if u]
                up_bench = [b for b, u in zip(benchmark, up_market) if u]
                down_fund = [r for r, d in zip(returns, down_market) if d]
                down_bench = [b for b, d in zip(benchmark, down_market) if d]
                
                if up_bench and mean(up_bench) > 0:
                    ratios.upside_capture = mean(up_fund) / mean(up_bench) * 100
                if down_bench and mean(down_bench) < 0:
                    ratios.downside_capture = mean(down_fund) / mean(down_bench) * 100
                if ratios.upside_capture is not None and ratios.downside_capture is not None:
                    if ratios.downside_capture != 0:
                        ratios.capture_ratio = ratios.upside_capture / ratios.downside_capture
        
        # Omega Ratio
        threshold = self.rf_daily
        gains = sum(r - threshold for r in returns if r > threshold)
        losses = sum(threshold - r for r in returns if r <= threshold)
        if losses > 0:
            ratios.omega_ratio = gains / losses
        
        # Max Drawdown
        ratios.max_drawdown = self._max_drawdown(returns)
        annual_return = (1 + mean_r) ** 252 - 1
        if ratios.max_drawdown and ratios.max_drawdown < 0:
            ratios.calmar_ratio = annual_return / abs(ratios.max_drawdown)
        
        # Avg Drawdown (Sterling)
        ratios.avg_drawdown = self._avg_drawdown(returns)
        if ratios.avg_drawdown and ratios.avg_drawdown < 0:
            ratios.sterling_ratio = annual_return / abs(ratios.avg_drawdown)
        
        # Burke Ratio
        drawdowns = self._all_drawdowns(returns)
        if drawdowns:
            dd_sq_sum = sum(d * d for d in drawdowns)
            if dd_sq_sum > 0:
                ratios.burke_ratio = annual_return / math.sqrt(dd_sq_sum)
        
        # Kappa 3
        ratios.kappa3_ratio = self._kappa_ratio(returns, moment=3)
        
        # Gain-Loss Ratio
        gains_r = [r for r in returns if r > 0]
        losses_r = [r for r in returns if r < 0]
        if gains_r and losses_r:
            ratios.gain_loss_ratio = mean(gains_r) / abs(mean(losses_r))
        
        # Upside Potential Ratio
        up_returns = [r for r in excess if r > 0]
        down_returns = [r for r in excess if r < 0]
        if up_returns and down_returns:
            up_potential = mean(up_returns)
            down_risk = math.sqrt(mean(r * r for r in down_returns))
            if down_risk > 0:
                ratios.upside_potential_ratio = up_potential / down_risk * math.sqrt(252)
        
        # CVaR / VaR 95%
        if n >= 20:
            var_95 = _percentile(returns, 5)
            ratios.var_95 = var_95
            tail_returns = [r for r in returns if r <= var_95]
            if tail_returns:
                ratios.cvar_95 = mean(tail_returns)
        
        # Tail Ratio
        p95 = _percentile(returns, 95)
        p05 = _percentile(returns, 5)
        if p05 < 0:
            ratios.tail_ratio = p95 / abs(p05)
        
        # Pain Index
        ratios.pain_index = abs(ratios.avg_drawdown) if ratios.avg_drawdown else None
        
        # Ulcer Index
        ratios.ulcer_index = self._ulcer_index(returns)
        
        # Skewness & Kurtosis (approximate)
        if n > 3:
            m3 = mean((r - mean_r) ** 3 for r in returns)
            m4 = mean((r - mean_r) ** 4 for r in returns)
            if std_r > 0:
                ratios.skewness = m3 / (std_r ** 3)
                ratios.kurtosis = m4 / (std_r ** 4) - 3  # excess kurtosis
        
        return ratios
    
    def _compute_beta(self, returns: Sequence[float], benchmark: Sequence[float]) -> float:
        """Compute beta via covariance/variance."""
        cov = _covariance(returns, benchmark)
        bench_var = _variance(benchmark)
        return cov / bench_var if bench_var > 0 else 0.0
    
    def _max_drawdown(self, returns: Sequence[float]) -> Optional[float]:
        """Maximum drawdown."""
        if len(returns) < 2:
            return None
        cumulative = [1.0]
        for r in returns:
            cumulative.append(cumulative[-1] * (1 + r))
        peak = cumulative[0]
        max_dd = 0.0
        for c in cumulative:
            peak = max(peak, c)
            if peak > 0:
                dd = c / peak - 1.0
                max_dd = min(max_dd, dd)
        return max_dd
    
    def _avg_drawdown(self, returns: Sequence[float]) -> Optional[float]:
        """Average drawdown."""
        if len(returns) < 2:
            return None
        cumulative = [1.0]
        for r in returns:
            cumulative.append(cumulative[-1] * (1 + r))
        peak = cumulative[0]
        drawdowns = []
        for c in cumulative:
            peak = max(peak, c)
            if peak > 0:
                dd = c / peak - 1.0
                if dd < 0:
                    drawdowns.append(dd)
        return mean(drawdowns) if drawdowns else 0.0
    
    def _all_drawdowns(self, returns: Sequence[float]) -> list[float]:
        """All drawdown values."""
        if len(returns) < 2:
            return []
        cumulative = [1.0]
        for r in returns:
            cumulative.append(cumulative[-1] * (1 + r))
        peak = cumulative[0]
        drawdowns = []
        for c in cumulative:
            peak = max(peak, c)
            if peak > 0:
                dd = c / peak - 1.0
                if dd < 0:
                    drawdowns.append(dd)
        return drawdowns
    
    def _ulcer_index(self, returns: Sequence[float]) -> Optional[float]:
        """Ulcer Index - RMS of drawdowns."""
        dds = self._all_drawdowns(returns)
        if not dds:
            return None
        return math.sqrt(mean(d * d for d in dds))
    
    def _kappa_ratio(self, returns: Sequence[float], moment: int = 3) -> Optional[float]:
        """Generalized Kappa ratio."""
        if len(returns) < 10:
            return None
        excess = [r - self.rf_daily for r in returns]
        lpm = mean(max(-r, 0) ** moment for r in excess)
        if lpm == 0:
            return None
        return mean(excess) / (lpm ** (1.0 / moment)) * math.sqrt(252)
    
    def _run_factor_models(
        self,
        returns: Sequence[float],
        benchmark: Sequence[float],
    ) -> dict[str, Any]:
        """Run simplified Fama-French 3-Factor and Carhart 4-Factor models."""
        results: dict[str, Any] = {}
        n = len(returns)
        if n < 60:
            return {"error": "Need at least 60 observations for factor models"}
        
        mkt_rf = [b - self.rf_daily for b in benchmark]
        y = [r - self.rf_daily for r in returns]
        
        # Simulated SMB, HML, MOM factors (in production fetch from Ken French library)
        random.seed(42)
        smb = [random.gauss(0, 0.005) for _ in range(n)]
        hml = [random.gauss(0, 0.005) for _ in range(n)]
        mom = [random.gauss(0, 0.005) for _ in range(n)]
        
        # FF3: multiple regression via sequential orthogonalization (simplified)
        # For pure Python, use simple approximation
        results["fama_french_3"] = self._multi_factor_regression(
            "Fama-French 3-Factor", y, [mkt_rf, smb, hml], ["mkt_rf", "smb", "hml"]
        )
        
        # Carhart 4-Factor
        results["carhart_4"] = self._multi_factor_regression(
            "Carhart 4-Factor", y, [mkt_rf, smb, hml, mom], ["mkt_rf", "smb", "hml", "mom"]
        )
        
        return results
    
    def _multi_factor_regression(
        self,
        name: str,
        y: list[float],
        factors: list[list[float]],
        factor_names: list[str],
    ) -> FactorModelResult:
        """Simplified multi-factor regression using sequential OLS."""
        n = len(y)
        k = len(factors) + 1  # +1 for intercept
        
        # Orthogonalize factors (Gram-Schmidt) for independent contributions
        orth_factors = []
        for f in factors:
            f_orth = f[:]
            for of in orth_factors:
                # Project f onto of and subtract
                cov_fo = _covariance(f_orth, of)
                var_o = _variance(of)
                if var_o > 0:
                    proj = cov_fo / var_o
                    f_orth = [fi - proj * oi for fi, oi in zip(f_orth, of)]
            orth_factors.append(f_orth)
        
        # Regress y on orthogonalized factors sequentially
        y_resid = y[:]
        betas = {}
        for i, (f, fname) in enumerate(zip(orth_factors, factor_names)):
            alpha, beta, _ = _ols_simple(f, y_resid)
            betas[fname] = beta
            y_resid = [yi - beta * fi for yi, fi in zip(y_resid, f)]
        
        # Alpha is mean of final residuals
        alpha = mean(y_resid)
        
        # R-squared
        ss_res = sum(ri ** 2 for ri in y_resid)
        y_mean = mean(y)
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k) if n > k else 0.0
        
        # Approximate t-stats
        mse = ss_res / max(1, n - k)
        alpha_t = alpha / math.sqrt(mse / n) if mse > 0 else 0.0
        
        beta_t_stats = {}
        for fname, beta in betas.items():
            # Rough standard error
            beta_t_stats[fname] = beta / math.sqrt(mse / n) if mse > 0 else 0.0
        
        f_stat = (r2 / (k - 1)) / ((1 - r2) / (n - k)) if r2 < 1 and n > k else None
        
        return FactorModelResult(
            model_name=name,
            alpha=alpha * 252,  # annualized
            alpha_t_stat=alpha_t,
            alpha_p_value=None,  # Would need scipy for exact
            betas=betas,
            beta_t_stats=beta_t_stats,
            r_squared=r2,
            adj_r_squared=adj_r2,
            f_statistic=f_stat,
            residuals=y_resid,
            n_obs=n,
        )
    
    def _compute_rolling_stability(
        self,
        returns: Sequence[float],
        benchmark: Optional[Sequence[float]] = None,
    ) -> dict[str, RollingStability]:
        """Compute rolling window stability."""
        results = {}
        
        for window in self.rolling_windows:
            if len(returns) < window + 10:
                continue
            
            rolling_sharpe = []
            rolling_sortino = []
            rolling_maxdd = []
            rolling_beta = []
            
            for i in range(window, len(returns) + 1):
                w_returns = returns[i - window:i]
                w_bench = benchmark[i - window:i] if benchmark is not None else None
                
                mean_r = mean(w_returns)
                std_r = stdev(w_returns) if len(w_returns) > 1 else 0.0
                excess = [r - self.rf_daily for r in w_returns]
                
                if std_r > 0:
                    rolling_sharpe.append(mean(excess) / std_r * math.sqrt(252))
                
                downside = [r for r in excess if r < 0]
                if len(downside) > 1:
                    downside_dev = stdev(downside)
                    if downside_dev > 0:
                        rolling_sortino.append(mean(excess) / downside_dev * math.sqrt(252))
                
                # Rolling max DD
                cum = [1.0]
                for r in w_returns:
                    cum.append(cum[-1] * (1 + r))
                peak = cum[0]
                max_dd = 0.0
                for c in cum:
                    peak = max(peak, c)
                    if peak > 0:
                        dd = c / peak - 1.0
                        max_dd = min(max_dd, dd)
                rolling_maxdd.append(max_dd)
                
                if w_bench is not None:
                    rolling_beta.append(self._compute_beta(w_returns, w_bench))
            
            for name, values in [
                ("sharpe", rolling_sharpe),
                ("sortino", rolling_sortino),
                ("max_drawdown", rolling_maxdd),
                ("beta", rolling_beta),
            ]:
                if values:
                    arr = values
                    stability = self._stability_score(arr)
                    
                    # Linear trend
                    x = list(range(len(arr)))
                    if len(arr) > 1:
                        # Simple linear regression slope
                        mx, my = mean(x), mean(arr)
                        cov_xy = _covariance(x, arr)
                        var_x = _variance(x)
                        trend = cov_xy / var_x if var_x > 0 else 0.0
                    else:
                        trend = None
                    
                    key = f"{name}_{window}d"
                    results[key] = RollingStability(
                        metric_name=name,
                        rolling_values=arr,
                        mean=mean(arr),
                        std=stdev(arr) if len(arr) > 1 else 0.0,
                        min_val=min(arr),
                        max_val=max(arr),
                        stability_score=stability,
                        trend=trend,
                    )
        
        return results
    
    def _stability_score(self, values: list[float]) -> float:
        """Compute stability score 0-100."""
        if len(values) < 2:
            return 50.0
        m = mean(values)
        s = stdev(values)
        if abs(m) < 1e-6:
            return 50.0
        cv = s / abs(m)
        score = 100 / (1 + cv * 2)
        return max(0.0, min(100.0, score))
    
    def _compute_category_relative(
        self,
        returns: Sequence[float],
        category_returns: dict[str, Sequence[Sequence[float]]],
    ) -> dict[str, CategoryRelativeScore]:
        """Morningstar-style category-relative scoring."""
        results = {}
        
        fund_ratios = self._compute_ratios(returns)
        fund_sharpe = fund_ratios.sharpe_ratio or 0
        
        for cat_name, peer_returns_list in category_returns.items():
            peer_sharpes = []
            for peer_r in peer_returns_list:
                if len(peer_r) >= self.min_obs:
                    ratios = self._compute_ratios(peer_r)
                    if ratios.sharpe_ratio is not None:
                        peer_sharpes.append(ratios.sharpe_ratio)
            
            if not peer_sharpes:
                continue
            
            percentile = sum(1 for ps in peer_sharpes if ps <= fund_sharpe) / len(peer_sharpes) * 100
            
            if percentile >= 90:
                stars = 5
            elif percentile >= 70:
                stars = 4
            elif percentile >= 40:
                stars = 3
            elif percentile >= 20:
                stars = 2
            else:
                stars = 1
            
            rank = sum(1 for ps in peer_sharpes if ps > fund_sharpe) + 1
            
            results[cat_name] = CategoryRelativeScore(
                category=cat_name,
                n_peers=len(peer_sharpes),
                percentile_rank=percentile,
                star_rating=stars,
                category_rank=rank,
                total_in_category=len(peer_sharpes),
            )
        
        return results
    
    def _composite_score(self, results: dict[str, Any]) -> float:
        """Composite score 0-100."""
        score = 50.0
        weights_sum = 0.0
        
        ratios = results.get("ratios")
        if isinstance(ratios, RiskAdjustedRatios):
            if ratios.sharpe_ratio is not None:
                sharpe_score = 50 + 45 * (1 - math.exp(-ratios.sharpe_ratio / 1.5))
                score += (sharpe_score - 50) * 0.25
                weights_sum += 0.25
            
            if ratios.sortino_ratio is not None:
                sortino_score = 50 + 45 * (1 - math.exp(-ratios.sortino_ratio / 1.5))
                score += (sortino_score - 50) * 0.15
                weights_sum += 0.15
            
            if ratios.omega_ratio is not None:
                omega_score = 50 + 30 * (1 - math.exp(-ratios.omega_ratio / 2))
                score += (omega_score - 50) * 0.10
                weights_sum += 0.10
            
            if ratios.cvar_95 is not None and ratios.cvar_95 < -0.02:
                score -= 10 * min(abs(ratios.cvar_95) / 0.05, 1)
                weights_sum += 0.10
            
            if ratios.capture_ratio is not None and ratios.capture_ratio > 1:
                cap_score = 50 + 20 * math.log(ratios.capture_ratio)
                score += (cap_score - 50) * 0.10
                weights_sum += 0.10
        
        factor_models = results.get("factor_models", {})
        if isinstance(factor_models, dict) and "fama_french_3" in factor_models:
            ff3 = factor_models["fama_french_3"]
            if isinstance(ff3, FactorModelResult):
                alpha_annual = ff3.alpha
                if alpha_annual > 0:
                    alpha_score = 50 + 30 * (1 - math.exp(-alpha_annual / 0.05))
                else:
                    alpha_score = 50 - 30 * (1 - math.exp(alpha_annual / 0.05))
                score += (alpha_score - 50) * 0.20
                weights_sum += 0.20
        
        rolling = results.get("rolling_stability", {})
        if isinstance(rolling, dict):
            stabilities = [v.stability_score for v in rolling.values() if isinstance(v, RollingStability)]
            if stabilities:
                avg_stability = mean(stabilities)
                score += (avg_stability - 50) * 0.15
                weights_sum += 0.15
        
        cat_rel = results.get("category_relative", {})
        if isinstance(cat_rel, dict):
            percentiles = [v.percentile_rank for v in cat_rel.values() if isinstance(v, CategoryRelativeScore)]
            if percentiles:
                avg_pct = mean(percentiles)
                score += (avg_pct - 50) * 0.10
                weights_sum += 0.10
        
        return max(0.0, min(100.0, score))


def analyze_fund(
    returns: Sequence[float],
    benchmark_returns: Optional[Sequence[float]] = None,
    category_returns: Optional[dict[str, Sequence[float]]] = None,
    risk_free_rate: float = 0.03,
) -> dict[str, Any]:
    """Convenience function for full fund analysis."""
    analyzer = AdvancedFundAnalyzer(risk_free_rate=risk_free_rate)
    return analyzer.analyze(returns, benchmark_returns, category_returns)