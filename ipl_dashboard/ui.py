"""Shared chart and table presentation."""

import plotly.express as px
import streamlit as st

COLORS = ["#55E0B5", "#82ACFF", "#F3B66B", "#C4A1FF", "#FF8499", "#A7CE7B", "#60D3EE"]


def label(column):
    return column.replace("_", " ").capitalize()


def hero(section, title, description):
    st.html(f'<div class="hero"><div class="eyebrow">{section}</div>'
            f'<h1>{title}</h1><p>{description}</p></div>')


def chart(frame, title, x, y, *, kind="bar", group=None, labels=None, horizontal=False, percent=False):
    if frame.empty:
        st.info("No records qualify for this view. Try widening the filters.")
        return
    chart_labels = {column: label(column) for column in frame.columns}
    chart_labels.update(labels or {})
    if kind == "line":
        frame = frame.sort_values(x)
    factory = {"bar": px.bar, "line": px.line}[kind]
    options = {"barmode": "group", "orientation": "h" if horizontal else "v"} if kind == "bar" else {}
    if kind == "line":
        options["markers"] = True
    fig = factory(frame, x=x, y=y, color=group, title=title, labels=chart_labels,
                  color_discrete_sequence=COLORS, **options)
    fig.update_layout(
        paper_bgcolor="#141F30", plot_bgcolor="#141F30", font_color="#E8EFF8",
        title=dict(x=.045, y=.95, font_size=17), margin=dict(l=16, r=18, t=65, b=20),
        height=400,
        legend=dict(orientation="h", y=-.24, title_text=""),
        hoverlabel=dict(bgcolor="#192940", font_color="#F1F7FF"),
    )
    fig.update_xaxes(gridcolor="#26374D", automargin=True)
    fig.update_yaxes(gridcolor="#26374D", automargin=True)
    if x == "season":
        fig.update_xaxes(type="category", categoryorder="category ascending")
    if horizontal:
        fig.update_yaxes(autorange="reversed")
        if percent:
            fig.update_xaxes(ticksuffix="%")
    elif percent:
        fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})


def ranking(frame, name, metric, title, *, ascending=False, unit=None, limit=10):
    top = frame.dropna(subset=[metric]).sort_values(
        [metric, name], ascending=[ascending, True]
    ).head(limit).round(2)
    chart(top, title, metric, name, horizontal=True, labels={metric: unit or label(metric)},
          percent=metric.endswith("pct"))


def table(frame, title, filename):
    st.subheader(title)
    if frame.empty:
        st.info("No rows match the current selection.")
        return
    display = frame.round(dict.fromkeys(frame.select_dtypes(include="floating").columns, 2))
    st.dataframe(display, hide_index=True, width="stretch",
                 column_config={column: label(column) for column in display.columns})
    st.download_button("Download CSV", display.to_csv(index=False).encode("utf-8"),
                       file_name=f"{filename}.csv", mime="text/csv", on_click="ignore")
