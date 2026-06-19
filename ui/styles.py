import streamlit as st


def apply_global_styles():
    st.markdown(
        """
        <style>
        .main {
            background-color: #f4f6fb;
        }

        h1, h2, h3 {
            font-weight: 600;
        }



        div[data-testid="metric-container"] {
            background-color: white;
            border: 1px solid #e6e8ef;
            padding: 18px;
            border-radius: 14px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
        }

        .section-card {
            background: white;
            padding: 22px;
            border-radius: 18px;
            border: 1px solid #e6e8ef;
            box-shadow: 0 4px 14px rgba(15,23,42,0.05);
            margin-bottom: 18px;
        }

        .risk-green {
            color: #16a34a;
            font-weight: 700;
        }

        .risk-yellow {
            color: #ca8a04;
            font-weight: 700;
        }

        .risk-red {
            color: #dc2626;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )