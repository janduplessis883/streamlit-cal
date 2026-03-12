import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px # Added for display_plot


def _normalized_merge_key(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.casefold()


def _build_normalized_sessions_df(
    surgery_counts: pd.DataFrame, surgeries_df: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    surgery_sizes = surgeries_df.copy()
    if "surgery" not in surgery_sizes.columns or "list_size" not in surgery_sizes.columns:
        return pd.DataFrame(), []

    surgery_sizes["merge_key"] = _normalized_merge_key(surgery_sizes["surgery"])
    surgery_sizes["list_size"] = pd.to_numeric(surgery_sizes["list_size"], errors="coerce")
    surgery_sizes = surgery_sizes[
        (surgery_sizes["merge_key"] != "") & surgery_sizes["list_size"].notna() & (surgery_sizes["list_size"] > 0)
    ].copy()
    surgery_sizes = surgery_sizes.drop_duplicates(subset="merge_key", keep="last")

    merged_df = surgery_counts.copy()
    merged_df["merge_key"] = _normalized_merge_key(merged_df["Surgery"])
    merged_df = merged_df.merge(
        surgery_sizes[["merge_key", "list_size"]],
        on="merge_key",
        how="left",
    )

    skipped_surgeries = merged_df.loc[merged_df["list_size"].isna(), "Surgery"].tolist()
    merged_df = merged_df.dropna(subset=["list_size"]).copy()
    if merged_df.empty:
        return pd.DataFrame(), skipped_surgeries

    merged_df["Normalized Sessions"] = (merged_df["Number of Sessions"] / merged_df["list_size"]) * 1000
    merged_df = merged_df.sort_values("Normalized Sessions", ascending=False)
    return merged_df, skipped_surgeries

def fair_share_plot(data: pd.DataFrame) -> None:
    """
    Plots a fair share bar chart using the provided DataFrame.

    Parameters:
    data (pd.DataFrame): DataFrame containing 'Name' and 'Fair Share' columns.
    """
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Name', y='Fair Share', data=data, palette='viridis')
    plt.title('Fair Share Distribution')
    plt.xlabel('Name')
    plt.ylabel('Fair Share')
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(plt)  # Display the plot in Streamlit

def display_plot(df, get_surgeries_data_func):
    st.subheader("Surgery Session Distribution")
    plot_type = st.session_state.get("plot_type", "Absolute Session Plot")

    # Ensure the DataFrame is not empty and contains required columns
    if df.empty or 'surgery' not in df.columns:
        st.info("No data available to display the plot.")
        return

    # Filter out rows where surgery is not specified or empty
    plot_df = df[df['surgery'].notna() & (df['surgery'] != '')].copy()

    if plot_df.empty:
        st.info("No booked sessions with surgery information available.")
        return

    # Count sessions per surgery
    surgery_counts = plot_df['surgery'].value_counts().reset_index()
    surgery_counts.columns = ['Surgery', 'Number of Sessions']

    if plot_type == "Normalized Sessions per 1000 pts":
        surgeries_df = get_surgeries_data_func()
        if surgeries_df.empty or 'list_size' not in surgeries_df.columns:
            st.warning("List size information is not available. Please add it in the 'Manage Surgeries' section.")
            return

        merged_df, skipped_surgeries = _build_normalized_sessions_df(surgery_counts, surgeries_df)
        if merged_df.empty:
            st.warning("No surgeries with a valid positive list size were found, so the normalized plot cannot be displayed.")
            return

        if skipped_surgeries:
            st.caption(
                "Skipped surgeries without a valid positive list size: "
                + ", ".join(sorted(skipped_surgeries))
            )

        mean_sessions = merged_df['Normalized Sessions'].mean()
        fig2 = px.bar(
            merged_df,
            x='Surgery',
            y='Normalized Sessions',
            title='Normalized Sessions per 1000 Patients',
            color='Surgery',
            template='plotly_white'
        )
        fig2.update_layout(
            xaxis_title="Surgery",
            yaxis_title="Sessions per 1000 Patients",
            showlegend=False,
            xaxis_tickangle=-45
        )
        fig2.add_hline(
            y=mean_sessions,
            line_dash="dash",
            line_width=0.8,
            line_color="#ae4f4d",
            annotation_text=f"Mean: {mean_sessions:.2f}",
            annotation_position="top right"
        )
    elif plot_type == "Absolute Session Plot": # Existing absolute plot
        fig2 = px.bar(
            surgery_counts,
            x='Surgery',
            y='Number of Sessions',
            title='Number of Sessions per Surgery',
            color='Surgery',  # Color bars by surgery name
            template='plotly_white', # Use a clean, modern template
        )
        fig2.update_layout(
            xaxis_title="Surgery",
            yaxis_title="Number of Sessions",
            showlegend=False, # Hide legend as colors are self-explanatory
            xaxis_tickangle=-45 # Angle the x-axis labels for better readability
        )
    elif plot_type == "Monthly Sessions":
        # Ensure 'Date' column is datetime
        plot_df['Date'] = pd.to_datetime(plot_df['Date'], errors='coerce')
        plot_df = plot_df.dropna(subset=['Date']) # Drop rows with invalid dates

        # Extract month and year for grouping
        plot_df['Month'] = plot_df['Date'].dt.to_period('M')

        # Group by surgery and month, then count sessions
        monthly_sessions = plot_df.groupby(['surgery', 'Month']).size().reset_index(name='Number of Sessions')
        monthly_sessions['Month'] = monthly_sessions['Month'].dt.to_timestamp() # Convert Period to Timestamp for plotting

        fig2 = px.scatter(
            monthly_sessions,
            x='Month',
            y='Number of Sessions',
            color='surgery',
            title='Monthly Sessions per Surgery',
            labels={'Month': 'Month', 'Number of Sessions': 'Number of Sessions', 'surgery': 'Surgery'},
            template='plotly_white'
        )
        fig2.update_layout(
            xaxis_title="Month",
            yaxis_title="Number of Sessions",
            hovermode="x unified",
            height=840
        )
        fig2.update_traces(marker=dict(size=16, line=dict(width=1, color='white')))
        fig2.update_xaxes(
            dtick="M1", # Show ticks for each month
            tickformat="%b\n%Y" # Format as Jan\n2025
        )

    st.plotly_chart(fig2, use_container_width=True, key="surgery_plot")

def display_normalized_sessions_plot(get_schedule_data_func, get_surgeries_data_func):
    df = get_schedule_data_func()
    plot_df = df[df['surgery'].notna() & (df['surgery'] != '')].copy()
    surgery_counts = plot_df['surgery'].value_counts().reset_index()
    surgery_counts.columns = ['Surgery', 'Number of Sessions']
    surgeries_df = get_surgeries_data_func()
    if surgeries_df.empty or 'list_size' not in surgeries_df.columns:
        st.warning("List size information is not available. Please add it in the 'Manage Surgeries' section.")
        return

    merged_df, skipped_surgeries = _build_normalized_sessions_df(surgery_counts, surgeries_df)
    if merged_df.empty:
        st.warning("No surgeries with a valid positive list size were found, so the normalized plot cannot be displayed.")
        return

    if skipped_surgeries:
        st.caption(
            "Skipped surgeries without a valid positive list size: "
            + ", ".join(sorted(skipped_surgeries))
        )

    mean_sessions = merged_df['Normalized Sessions'].mean()

    fig = px.bar(
        merged_df,
        x='Surgery',
        y='Normalized Sessions',
        title='Normalized Sessions per 1000 Patients',
        color='Surgery',
        template='plotly_white'
    )
    fig.update_layout(
        xaxis_title="Surgery",
        yaxis_title="Sessions per 1000 Patients",
        showlegend=False,
        xaxis_tickangle=-45
    )
    # Add horizontal line at mean_sessions
    fig.add_hline(
        y=mean_sessions,
        line_dash="dash",
        line_width=0.8,
        line_color="#ae4f4d",
        annotation_text=f"Mean: {mean_sessions:.2f}",
        annotation_position="top right"
    )
    st.plotly_chart(fig, use_container_width=True, key="user_plot")
