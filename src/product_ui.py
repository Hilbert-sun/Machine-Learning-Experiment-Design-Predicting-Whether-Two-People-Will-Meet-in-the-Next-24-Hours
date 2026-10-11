"""Shared display helpers; never cache, store or calculate questionnaire values."""
import textwrap
import streamlit as st

ICONS = {'frequency':'🕰️', 'distance':'📍', 'area':'🧭', 'timing':'⏱️', 'recency':'🗓️'}


def keyword_cards(keywords):
    for offset in range(0, len(keywords), 3):
        for column, card in zip(st.columns(3), keywords[offset:offset + 3]):
            with column:
                with st.container(border=True):
                    st.caption(ICONS.get(card.field, '🔎') + ' ' + card.direction)
                    st.subheader(card.name)
                    st.write(card.source)
                    st.write(card.explanation)


def readable_figure(figure):
    # Presentation only: retain all values, gaps, provenance and hover data.
    title = figure.layout.title.text or ''
    figure.update_layout(title={'text':'<br>'.join(textwrap.wrap(title, 18)), 'font':{'size':16}},
                         margin={'l':12, 'r':12, 't':90, 'b':65}, autosize=True)
    return figure
