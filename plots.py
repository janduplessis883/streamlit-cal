import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px # Added for display_plot

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

    # Moved plot type selection here
    plot_type = st.sidebar.radio("Select Plot Type", ["Absolute Session Plot", "Normalized Sessions per 1000 pts", "Monthly Sessions"], key="plot_type_radio_in_plot")

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

        # Merge dataframes to get list sizes
        merged_df = pd.merge(surgery_counts, surgeries_df, left_on='Surgery', right_on='surgery', how='left')
        merged_df['list_size'] = pd.to_numeric(merged_df['list_size'], errors='coerce').fillna(0) # Ensure numeric
        merged_df['list_size'] = merged_df['list_size'].replace(0, 1) # Avoid division by zero
        merged_df['Normalized Sessions'] = (merged_df['Number of Sessions'] / merged_df['list_size']) * 1000
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
    elif plot_type == "Monthly Sessions": # New monthly sessions plot
        # Ensure 'Date' column is datetime
        plot_df['Date'] = pd.to_datetime(plot_df['Date'], errors='coerce')
        plot_df = plot_df.dropna(subset=['Date']) # Drop rows with invalid dates

        # Extract month and year for grouping
        plot_df['Month'] = plot_df['Date'].dt.to_period('M')

        # Group by surgery and month, then count sessions
        monthly_sessions = plot_df.groupby(['surgery', 'Month']).size().reset_index(name='Number of Sessions')
        monthly_sessions['Month'] = monthly_sessions['Month'].dt.to_timestamp() # Convert Period to Timestamp for plotting

        fig2 = px.line(
            monthly_sessions,
            x='Month',
            y='Number of Sessions',
            color='surgery',
            title='Number of Sessions per Month per Surgery',
            labels={'Month': 'Month', 'Number of Sessions': 'Number of Sessions', 'surgery': 'Surgery'},
            template='plotly_white'
        )
        fig2.update_layout(
            xaxis_title="Month",
            yaxis_title="Number of Sessions",
            hovermode="x unified"
        )
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

    # Merge dataframes to get list sizes
    merged_df = pd.merge(surgery_counts, surgeries_df, left_on='Surgery', right_on='surgery', how='left')
    merged_df['list_size'] = merged_df['list_size'].replace(0, 1) # Avoid division by zero
    merged_df['Normalized Sessions'] = (merged_df['Number of Sessions'] / merged_df['list_size']) * 1000

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
