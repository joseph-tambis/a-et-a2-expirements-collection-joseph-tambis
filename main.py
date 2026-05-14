import pandas as pd                     # Data manipulation and CSV handling
import numpy as np                      # Numerical operations and array handling
import seaborn as sns                   # High-level statistical data visualization
import matplotlib.pyplot as plt         # Core plotting engine
import matplotlib.gridspec as gridspec  # Advanced subplot layout management
from math import pi                     # Required for circular geometry in radar charts
import warnings

# Suppress non-critical library warnings
warnings.filterwarnings("ignore")

# ── Global Style ──────────────────────────────────────────────────────────────
# Define the dark theme color palette and standardized font sizes
DARK_BG, PANEL_BG, TEXT_COL, GRID_COL = "#0F1724", "#162033", "#E8EDF5", "#263350"
DEV_COL, DEVG_COL, ACCENT = "#42A5F5", "#FF7043", "#00E5CC"
DASH_TITLE_WHITE = "#FFFFFF"

TITLE_SIZE = 18
DASH_TITLE_SIZE = 9

# Apply style settings to Matplotlib's runtime configuration for global consistency
plt.rcParams.update({
    "figure.facecolor": DARK_BG, "axes.facecolor": PANEL_BG, "axes.edgecolor": GRID_COL,
    "axes.labelcolor": TEXT_COL, "xtick.color": TEXT_COL, "ytick.color": TEXT_COL,
    "grid.color": GRID_COL, "text.color": TEXT_COL, "figure.autolayout": False,
    "font.family": "sans-serif"
})

# ── 1. Data Prep ─────────────────────────────────────────────────────────────
# Load dataset and standardize column naming (snake_case)
df = pd.read_csv("Life Expectancy Data.csv")
df.columns = df.columns.str.strip().str.replace(" ", "_").str.lower()
df.dropna(subset=["life_expectancy"], inplace=True)

# Missing value imputation: Use country-specific medians to preserve geographic trends
num_cols = df.select_dtypes(include=np.number).columns.tolist()
df[num_cols] = df.groupby("country")[num_cols].transform(lambda x: x.fillna(x.median()))
# Fallback imputation using global median for any remaining gaps
df[num_cols] = df[num_cols].fillna(df[num_cols].median())

# Refactor feature names for brevity in chart legends and titles
df.rename(columns={
    "life_expectancy": "life_exp", 
    "income_composition_of_resources": "hdi_income",
    "total_expenditure": "health_exp"
}, inplace=True)

# Create temporal segments to visualize data evolution across three distinct periods
df["period"] = pd.cut(df["year"], bins=[1999, 2004, 2009, 2015], labels=["2000–04", "2005–09", "2010–15"])

# Define column groups for specific analytical modules
HEATMAP_COLS = ["life_exp", "adult_mortality", "health_exp", "hdi_income", "schooling", "gdp"]
RADAR_COLS = ["life_exp", "schooling", "hdi_income", "health_exp", "bmi"]
RADAR_LABELS = ["Life Exp", "Schooling", "HDI", "Health Exp", "BMI"]

# ── Shared Logic ──────────────────────────────────────────────────────────────
def get_radar_data(data_df):
    """Calculates status-based means and performs min-max normalization for radar scaling."""
    radar_df = data_df.groupby("status")[RADAR_COLS].mean()
    radar_norm = (radar_df - data_df[RADAR_COLS].min()) / (data_df[RADAR_COLS].max() - data_df[RADAR_COLS].min())
    return radar_norm

def draw_radar(ax, data, title, is_dashboard=False):
    """Constructs a polar chart comparing Developed vs. Developing country profiles."""
    N = len(RADAR_LABELS)
    # Calculate angular spacing for axes on the circular plot
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1] # Ensure the polygon closes
    
    ax.set_theta_offset(pi / 2)
    ax.set_theta_direction(-1) # Clockwise orientation
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(RADAR_LABELS, size=(6 if is_dashboard else 10), color=TEXT_COL)
    
    ax.set_rlabel_position(0)
    plt.yticks([0.2, 0.4, 0.6, 0.8], ["20%","40%","60%","80%"], color="#556677", size=5)
    plt.ylim(0, 1)
    
    # Plot data points and fill area for each country category
    for status, color in zip(["Developed", "Developing"], [DEV_COL, DEVG_COL]):
        values = data.loc[status].values.flatten().tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=1.5, linestyle='solid', label=status, color=color)
        ax.fill(angles, values, color=color, alpha=0.2)
        
    title_color = DASH_TITLE_WHITE if is_dashboard else ACCENT
    ax.set_title(title, weight='bold', size=(DASH_TITLE_SIZE if is_dashboard else TITLE_SIZE), color=title_color, pad=15)

# ── Main Application ─────────────────────────────────────────────────────────
class GlobalHealthStory:
    """Class to manage the interactive data storytelling slideshow."""
    def __init__(self, df):
        self.df = df
        self.page = 0
        self.total_pages = 8
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.canvas.manager.set_window_title("Artifact 2: Visualizing Global Health")
        
        # Free up arrow keys from default Matplotlib behavior
        try:
            plt.rcParams['keymap.back'].remove('left')
            plt.rcParams['keymap.forward'].remove('right')
        except: pass
        
        # Connect key press events to navigation logic
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        self.draw()

    def draw(self):
        """Main rendering engine that updates the plot based on self.page."""
        self.fig.clear()
        idx = self.page
        radar_data = get_radar_data(self.df)

        if idx < 7: # Render individual story pages (1-7)
            ax = self.fig.add_subplot(111) if idx != 1 and idx != 6 else None
            if idx == 0: # Time-series trend of life expectancy
                trend = self.df.groupby(["year", "status"])["life_exp"].mean().reset_index()
                sns.lineplot(data=trend, x="year", y="life_exp", hue="status", palette=[DEV_COL, DEVG_COL], linewidth=4, marker="o", ax=ax)
                ax.set_title("1. Global Life Expectancy Trend Over Time", fontweight='bold', fontsize=TITLE_SIZE, color=ACCENT, pad=35)
            elif idx == 1: # Horizontal bar comparison of outliers
                gs = gridspec.GridSpec(1, 2, figure=self.fig, wspace=0.35)
                ax1, ax2 = self.fig.add_subplot(gs[0, 0]), self.fig.add_subplot(gs[0, 1])
                avg = self.df.groupby("country")["life_exp"].mean().sort_values()
                sns.barplot(x=avg.tail(15).values, y=avg.tail(15).index, palette="Blues_r", ax=ax1)
                sns.barplot(x=avg.head(15).values, y=avg.head(15).index, palette="Oranges", ax=ax2)
                ax1.set_title("Top 15 Countries", fontweight='bold', color=ACCENT, fontsize=14)
                ax2.set_title("Bottom 15 Countries", fontweight='bold', color=ACCENT, fontsize=14)
                self.fig.suptitle("2. Top & Bottom 15 Countries", fontweight='bold', color=ACCENT, y=0.96, fontsize=TITLE_SIZE)
            elif idx == 2: # Scatter relationship between schooling and longevity
                sns.scatterplot(data=self.df, x="schooling", y="life_exp", hue="status", size="hdi_income", sizes=(20, 500), alpha=0.5, palette=[DEVG_COL, DEV_COL], ax=ax)
                ax.set_title("3. Schooling vs. Life Expectancy", fontweight='bold', color=ACCENT, pad=35, fontsize=TITLE_SIZE)
            elif idx == 3: # Statistical correlation matrix
                sns.heatmap(self.df[HEATMAP_COLS].corr(), annot=True, cmap="RdYlGn", center=0, ax=ax)
                ax.set_title("4. Correlation Matrix of Health Indicators", fontweight='bold', color=ACCENT, pad=35, fontsize=TITLE_SIZE)
            elif idx == 4: # Boxplots showing data distribution across periods
                sns.boxplot(data=self.df, x="period", y="life_exp", hue="status", palette=[DEVG_COL, DEV_COL], ax=ax)
                ax.set_title("5. Life Expectancy Distribution by Period", fontweight='bold', color=ACCENT, pad=35, fontsize=TITLE_SIZE)
            elif idx == 5: # Density estimation of mortality rates
                for s, c in zip(["Developing", "Developed"], [DEVG_COL, DEV_COL]):
                    sns.kdeplot(self.df[self.df["status"]==s]["adult_mortality"], fill=True, color=c, label=s, ax=ax)
                # ADDED LEGEND HERE: Displays country categories clearly on page 6
                ax.legend(title="Country Status", facecolor=PANEL_BG, edgecolor=GRID_COL)
                ax.set_title("6. Adult Mortality Rate Distribution", fontweight='bold', color=ACCENT, pad=35, fontsize=TITLE_SIZE)
            elif idx == 6: # Large format Radar Chart
                ax_rad = self.fig.add_subplot(111, polar=True)
                draw_radar(ax_rad, radar_data, "7. Status Profile Radar Chart Comparison")
                ax_rad.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))

        else: # Render Page 8: The Comprehensive Dashboard Summary
            self.fig.suptitle("GLOBAL HEALTH — FULL SUMMARY DASHBOARD", color=ACCENT, fontsize=20, fontweight='bold', y=0.98)
            # Use GridSpec to define a 4-row, 2-column layout
            gs = gridspec.GridSpec(4, 2, figure=self.fig, hspace=0.6, wspace=0.3)
            
            # Subplot A1: Historical Trends
            a1 = self.fig.add_subplot(gs[0, 0])
            sns.lineplot(data=self.df.groupby(["year", "status"])["life_exp"].mean().reset_index(), x="year", y="life_exp", hue="status", palette=[DEV_COL, DEVG_COL], ax=a1, legend=False)
            
            # Sub-layout for mini bar charts
            gs_inner = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs[1, 0], wspace=0.4)
            a2a, a2b = self.fig.add_subplot(gs_inner[0, 0]), self.fig.add_subplot(gs_inner[0, 1])
            avg = self.df.groupby("country")["life_exp"].mean().sort_values()
            a2a.barh(avg.tail(8).index, avg.tail(8).values, color=DEV_COL)
            a2b.barh(avg.head(8).index, avg.head(8).values, color=DEVG_COL)
            a2a.set_title("2a. Top", fontsize=7, color=DASH_TITLE_WHITE, fontweight='bold')
            a2b.set_title("2b. Bottom", fontsize=7, color=DASH_TITLE_WHITE, fontweight='bold')
            
            # Subplot A3: Socio-economic Scatter
            a3 = self.fig.add_subplot(gs[2, 0])
            sns.scatterplot(data=self.df, x="schooling", y="life_exp", hue="status", palette=[DEVG_COL, DEV_COL], s=1, alpha=0.2, ax=a3, legend=False)
            
            # Subplot A4: Matrix of dependencies
            a4 = self.fig.add_subplot(gs[3, 0])
            sns.heatmap(self.df[HEATMAP_COLS].corr(), annot=True, cmap="RdYlGn", center=0, cbar=False, ax=a4, annot_kws={"size": 6})

            # Subplot A5: Boxplot distributions
            a5 = self.fig.add_subplot(gs[0, 1])
            sns.boxplot(data=self.df, x="period", y="life_exp", hue="status", palette=[DEVG_COL, DEV_COL], ax=a5)
            a5.get_legend().remove()
            
            # Subplot A6: Mortality Density Curves
            a6 = self.fig.add_subplot(gs[1, 1])
            for s, c in zip(["Developing", "Developed"], [DEVG_COL, DEV_COL]):
                sns.kdeplot(self.df[self.df["status"]==s]["adult_mortality"], color=c, label=s, ax=a6)
            # ADDED MINI LEGEND TO DASHBOARD: Small legend for multi-axis readability
            a6.legend(fontsize=6, title_fontsize=6, loc='upper right')
            
            # Subplot A7: Status Profiles (Radar)
            a7 = self.fig.add_subplot(gs[2:4, 1], polar=True)
            draw_radar(a7, radar_data, "7. Status Profile Radar Chart Comparison", is_dashboard=True)

            # Define dashboard title list for automated iterative labeling
            dash_titles = [
                "1. Global Life Expectancy Trend Over Time", "2. Top & Bottom 15 Countries", 
                "3. Schooling vs. Life Expectancy", "4. Correlation Matrix of Health Indicators",
                "5. Life Expectancy Distribution by Period", "6. Adult Mortality Rate Distribution"
            ]
            # Standardize font sizes and remove redundant axis labels for dashboard clarity
            for ax, t in zip([a1, a2a, a3, a4, a5, a6], dash_titles):
                if ax != a2a:
                    ax.set_title(t, fontsize=DASH_TITLE_SIZE, color=DASH_TITLE_WHITE, fontweight='bold')
                ax.tick_params(labelsize=7); ax.set_xlabel(""); ax.set_ylabel("")

        # Render page tracking and navigation footer
        self.fig.text(0.5, 0.02, f"PAGE {self.page + 1} OF {self.total_pages}   |   NAVIGATE WITH ← AND → ARROW KEYS", ha="center", color="#8899BB", fontsize=10, fontweight='bold')
        plt.subplots_adjust(top=0.92, bottom=0.08, left=0.1, right=0.9)
        self.fig.canvas.draw()

    def on_key(self, event):
        """Listener function to handle page switching via keyboard input."""
        if event.key == 'right': self.page = (self.page + 1) % self.total_pages
        elif event.key == 'left': self.page = (self.page - 1) % self.total_pages
        self.draw()

if __name__ == "__main__":
    # Entry point of the script: Init and display the visualization app
    app = GlobalHealthStory(df)
    plt.show()