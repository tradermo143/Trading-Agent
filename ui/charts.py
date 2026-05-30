"""
Plotly chart builders for the approval UI.
Each function returns a plain Python dict {data, layout} — serialised to JSON by the Flask route.
"""
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from screener.indicators import sma as _sma

# ── Colour palette (GitHub-dark inspired) ────────────────────────────────────
_BG      = '#0d1117'
_PLOT    = '#161b22'
_GRID    = '#21262d'
_TEXT    = '#c9d1d9'
_UP      = '#3fb950'
_DOWN    = '#f85149'
_SMA20   = '#388bfd'
_SMA50   = '#d29922'
_SMA200  = '#f85149'
_ZONE    = 'rgba(255, 235, 59, 0.15)'
_ZONE_BD = 'rgba(255, 193, 7, 0.6)'


def _date_str(d) -> str:
    """Normalise a date-like value to 'YYYY-MM-DD' string."""
    if hasattr(d, 'strftime'):
        return d.strftime('%Y-%m-%d')
    return str(d)[:10]


def _base_layout(title: str = '') -> dict:
    return dict(
        title=dict(text=title, font=dict(size=12, color=_TEXT), x=0.01, xanchor='left'),
        height=360,
        margin=dict(l=8, r=96, t=28, b=8),
        paper_bgcolor=_BG,
        plot_bgcolor=_PLOT,
        font=dict(color=_TEXT, size=11),
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='left', x=0,
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=11),
        ),
    )


def _build_ohlcv(df: pd.DataFrame) -> go.Figure:
    """Base 2-row figure: candlestick + volume."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.73, 0.27],
        vertical_spacing=0.02,
    )

    xs = df.index.strftime('%Y-%m-%d').tolist()

    fig.add_trace(go.Candlestick(
        x=xs,
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing=dict(line_color=_UP,   fillcolor=_UP),
        decreasing=dict(line_color=_DOWN, fillcolor=_DOWN),
        name='Price', showlegend=False,
    ), row=1, col=1)

    for col, color, label in [('sma20', _SMA20, 'SMA 20'),
                               ('sma50', _SMA50, 'SMA 50'),
                               ('sma200', _SMA200, 'SMA 200')]:
        s = df.get(col)
        if s is not None and s.notna().any():
            fig.add_trace(go.Scatter(
                x=xs, y=s.tolist(),
                mode='lines', name=label,
                line=dict(color=color, width=1.4),
            ), row=1, col=1)

    vol_colors = [_UP if c >= o else _DOWN
                  for c, o in zip(df['close'], df['open'])]
    fig.add_trace(go.Bar(
        x=xs, y=df['volume'].tolist(),
        marker_color=vol_colors, opacity=0.65,
        name='Vol', showlegend=False,
    ), row=2, col=1)

    # type='category' tells Plotly to only render dates that exist in the data,
    # which removes the blank gaps for weekends and market holidays.
    fig.update_xaxes(
        type='category',
        nticks=10,
        tickangle=-30,
        gridcolor=_GRID, linecolor=_GRID, showgrid=True,
    )
    fig.update_yaxes(gridcolor=_GRID, linecolor=_GRID, showgrid=True)

    return fig


def _fig_to_dict(fig: go.Figure) -> dict:
    """Serialise figure via plotly.io to handle numpy / Timestamp types."""
    raw = json.loads(pio.to_json(fig))
    return {'data': raw['data'], 'layout': raw['layout']}


# ── Public chart builders ────────────────────────────────────────────────────

def build_daily(df: pd.DataFrame, zone: dict, n_bars: int = 150) -> dict:
    """
    Daily candlestick chart with SMA overlays, contraction zone shading,
    and entry / stop horizontal lines.
    Returns a plain dict ready for jsonify().
    """
    df = df.tail(n_bars).copy()
    fig = _build_ohlcv(df)

    # Contraction zone shading
    fig.add_vrect(
        x0=_date_str(zone['zone_start_date']),
        x1=_date_str(zone['zone_end_date']),
        fillcolor=_ZONE,
        line_width=1, line_color=_ZONE_BD,
        annotation_text='Zone',
        annotation_position='top left',
        annotation_font=dict(color='#FFC107', size=10),
        row=1, col=1,
    )

    # Entry line
    fig.add_hline(
        y=zone['entry_price'],
        line_dash='dot', line_color=_UP, line_width=1.6,
        annotation_text=f"  Entry  ${zone['entry_price']:.2f}",
        annotation_position='right',
        annotation_font=dict(color=_UP, size=11),
        row=1, col=1,
    )

    # Stop line
    fig.add_hline(
        y=zone['stop_price'],
        line_dash='dot', line_color=_DOWN, line_width=1.6,
        annotation_text=f"  Stop  ${zone['stop_price']:.2f}",
        annotation_position='right',
        annotation_font=dict(color=_DOWN, size=11),
        row=1, col=1,
    )

    fig.update_layout(**_base_layout('Daily'))
    return _fig_to_dict(fig)


def build_weekly(df: pd.DataFrame, n_bars: int = 150) -> dict:
    """
    Weekly candlestick chart.
    Moving averages are the daily 20d/50d/200d SMAs resampled to weekly
    frequency — identical values to the daily chart for direct comparison.
    """
    # Weekly OHLCV candlesticks
    weekly = (df
              .resample('W-FRI')
              .agg({'open': 'first', 'high': 'max',
                    'low': 'min', 'close': 'last', 'volume': 'sum'})
              .dropna())

    # Carry daily SMA values to weekly (take Friday's daily value each week)
    for col in ('sma20', 'sma50', 'sma200'):
        if col in df.columns:
            weekly[col] = df[col].resample('W-FRI').last()

    weekly = weekly.tail(n_bars)

    fig = _build_ohlcv(weekly)
    fig.update_layout(**_base_layout('Weekly'))
    return _fig_to_dict(fig)
