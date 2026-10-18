"""Chronological multi-step forecasting with fair baselines.

All models predict the ENTIRE last 60-month validation block without seeing
its targets. This block selects a model: it is not an independent test set.
Ridge uses only deterministic future-known calendar/time features. Exploratory
centred rolling means, full-record climatologies and ENSO proxies NEVER enter
this module. Missing training targets are forward filled within training only;
validation metrics exclude originally missing observations.
"""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from . import config as cfg


def evaluate(y_true, y_pred) -> dict:
    """Celsius MAPE is omitted: percentages depend on the arbitrary zero."""
    a, b = np.asarray(y_true, float), np.asarray(y_pred, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if not len(a):
        raise ValueError('No observed targets available for evaluation')
    e = a - b
    return dict(MAE=float(np.abs(e).mean()), RMSE=float(np.sqrt((e**2).mean())),
                R2=float(1-(e**2).sum()/((a-a.mean())**2).sum()) if a.std() else np.nan,
                n_evaluated=int(len(a)))


def naive_forecast(train, h):
    return np.repeat(train[-1], h)


def seasonal_naive_forecast(train, h, period=12):
    if len(train) < period:
        raise ValueError('Seasonal naive needs at least one year')
    return np.resize(np.asarray(train)[-period:], h)


def drift_forecast(train, h):
    return train[-1] + (train[-1]-train[0])/max(len(train)-1, 1)*np.arange(1,h+1)


def _calendar(dates):
    """Only known future covariates, no measurements of the future."""
    d = pd.DatetimeIndex(dates)
    t = (d.year.to_numpy()-1980)*12 + d.month.to_numpy()-1
    ang = 2*np.pi*d.month.to_numpy()/12
    return np.column_stack([t, np.sin(ang), np.cos(ang)])


def build_ml_dataset(df, target='temp_mean_c'):
    """Educational helper: no target-derived or centred features allowed."""
    d = df.sort_values('date').copy()
    d[['time_index','month_sin','month_cos']] = _calendar(d.date)
    return d, ['time_index','month_sin','month_cos']


def _ridge_fit(dates, values):
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    pipe = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    return pipe.fit(_calendar(dates), values)


def _observations(d, target):
    # Historical interpolation is NOT used to evaluate or fit the forecaster.
    name = 'observed_temp_mean_c' if target == 'temp_mean_c' and 'observed_temp_mean_c' in d else target
    return d[name].astype(float).to_numpy()


def _fill_train(a):
    s = pd.Series(a).ffill()
    if s.isna().all():
        raise ValueError('Training series has no observations')
    return s.fillna(s.median()).to_numpy()


def ml_forecast(df, target='temp_mean_c', h=cfg.FORECAST_HORIZON, test_size=cfg.TEST_SIZE):
    """Calendar Ridge: identical fixed-origin protocol for validation/future."""
    d = df.sort_values('date').copy()
    y = _observations(d, target)
    cut = len(d)-test_size
    pipe = _ridge_fit(d.date.iloc[:cut], _fill_train(y[:cut]))
    pred = pipe.predict(_calendar(d.date.iloc[cut:]))
    metrics = evaluate(y[cut:], pred)
    pipe = _ridge_fit(d.date, _fill_train(y))
    dates = pd.date_range(d.date.max()+pd.offsets.MonthBegin(), periods=h, freq='MS')
    future = pd.DataFrame({'date':dates, 'prediction':pipe.predict(_calendar(dates))})
    return dict(model='Ridge (calendar + trend)', metrics=metrics, forecast=future,
                fitted=pipe, features=['time_index','month_sin','month_cos'],
                validation_prediction=pred)


def arima_forecast(series, h=cfg.FORECAST_HORIZON, order=(1,1,1), test_size=cfg.TEST_SIZE):
    from statsmodels.tsa.arima.model import ARIMA
    y = np.asarray(series, float)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            fit = ARIMA(_fill_train(y[:-test_size]), order=order).fit()
            pred = np.asarray(fit.forecast(test_size))
            full = ARIMA(_fill_train(y), order=order).fit()
            fc = full.get_forecast(h)
        ci = np.asarray(fc.conf_int())
        return dict(model=f'ARIMA{order}', metrics=evaluate(y[-test_size:],pred),
                    forecast_mean=np.asarray(fc.predicted_mean), forecast_ci_low=ci[:,0],
                    forecast_ci_high=ci[:,1], order=order, validation_prediction=pred)
    except (ValueError, np.linalg.LinAlgError):
        return {}


def arima_grid_search(series, h=cfg.FORECAST_HORIZON, test_size=cfg.TEST_SIZE):
    """Choose order by TRAINING AIC, not repeated peeking at validation."""
    from statsmodels.tsa.arima.model import ARIMA
    train = _fill_train(np.asarray(series,float)[:-test_size])
    best, score = (1,1,1), np.inf
    for p in range(cfg.ARIMA_MAX_P+1):
        for dd in (0,1):
            for q in range(cfg.ARIMA_MAX_Q+1):
                if (p,dd,q)==(0,0,0):
                    continue
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        fit = ARIMA(train, order=(p,dd,q)).fit()
                    if fit.mle_retvals.get('converged',True) and fit.aic < score:
                        best, score = (p,dd,q), fit.aic
                except (ValueError, np.linalg.LinAlgError):
                    continue
    return arima_forecast(series,h,best,test_size)


def forecast_region(df_region, target='temp_mean_c', h=cfg.FORECAST_HORIZON, test_size=cfg.TEST_SIZE):
    d = df_region.sort_values('date').copy()
    if len(d)<test_size+36:
        return {}
    if not d.date.diff().dropna().dt.days.between(28,31).all():
        raise ValueError('Forecasting requires a complete monthly date grid')
    y = _observations(d,target)
    train = _fill_train(y[:-test_size]); full = _fill_train(y)
    records, forecasts, validation = [], {}, {}
    for name, fun in [('Naive',naive_forecast),('Seasonal naive',seasonal_naive_forecast),('Drift (linear)',drift_forecast)]:
        val = fun(train,test_size)
        records.append(dict(model=name,**evaluate(y[-test_size:],val)))
        forecasts[name] = fun(full,h); validation[name]=val
    ml = ml_forecast(d,target,h,test_size)
    records.append(dict(model=ml['model'],**ml['metrics']))
    forecasts[ml['model']] = ml['forecast'].prediction.to_numpy()
    validation[ml['model']] = ml['validation_prediction']
    arima = arima_grid_search(pd.Series(y),h,test_size)
    if arima:
        records.append(dict(model=arima['model'],**arima['metrics']))
        forecasts[arima['model']]=arima['forecast_mean']
        validation[arima['model']]=arima['validation_prediction']
    metrics = pd.DataFrame(records).sort_values('RMSE').reset_index(drop=True)
    best = metrics.iloc[0]['model']; pred = forecasts[best]
    dates = pd.date_range(d.date.max()+pd.offsets.MonthBegin(),periods=h,freq='MS')
    # Approximate residual bands, NOT a calibrated physical climate interval.
    half_width = 1.96*float(metrics.iloc[0]['RMSE'])
    lo, hi = pred-half_width, pred+half_width
    if arima and best==arima['model']:
        lo,hi = arima['forecast_ci_low'],arima['forecast_ci_high']
    fc = pd.DataFrame(dict(region=d.region.iloc[0],date=dates,prediction=pred,
                           ci_low=lo,ci_high=hi,model=best,target=target,
                           interval_method='ARIMA model-based' if best.startswith('ARIMA') else 'approximate 1.96 x validation RMSE; not calibrated'))
    return dict(region=d.region.iloc[0],best_model=best,metrics=metrics,forecast=fc,
                arima=arima,ml=ml,history=d[['date',target]].copy())


def run_forecasting(df, target='temp_mean_c', h=cfg.FORECAST_HORIZON, test_size=cfg.TEST_SIZE):
    results = [forecast_region(g,target,h,test_size) for _,g in df.groupby('region')]
    results = [r for r in results if r]
    metrics, forecasts = [], []
    for r in results:
        m = r['metrics'].assign(region=r['region']); metrics.append(m); forecasts.append(r['forecast'])
    return dict(metrics=pd.concat(metrics,ignore_index=True) if metrics else pd.DataFrame(),
                forecast=pd.concat(forecasts,ignore_index=True) if forecasts else pd.DataFrame(),
                results=results,target=target)
