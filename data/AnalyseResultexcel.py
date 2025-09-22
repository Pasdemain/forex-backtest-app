import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os

# Fonction pour sélectionner un fichier
def select_file():
    root = tk.Tk()
    root.withdraw()  # Cacher la fenêtre principale
    file_path = filedialog.askopenfilename(title="Select SQLite Database", filetypes=[("SQLite files", "*.db")])
    return file_path

# Appeler la fonction pour sélectionner le fichier
database_path = select_file()

# Extraire le nom du fichier sans extension pour l'utiliser dans le nom du fichier Excel
file_name = os.path.splitext(os.path.basename(database_path))[0]

# Connexion à la base de données SQLite sélectionnée
conn = sqlite3.connect(database_path)

# Chargement des données dans un DataFrame
df = pd.read_sql_query("SELECT * FROM trading_entries", conn)

# Ajouter des colonnes pour l'année et le mois à partir de 'StartDatetime'
df['YearMonth'] = pd.to_datetime(df['StartDatetime']).dt.to_period('M')

# Fonction pour calculer les pourcentages de gains/pertes
def calculate_percentage(row, risk):
    ratio = row['TradeRatio'].split(':')
    win_ratio = int(ratio[1])
    if row['Result'] == 'Winning':
        return risk * win_ratio
    else:
        return -risk

# Ajouter une colonne 'Percentage' pour chaque niveau de risque avant les calculs
for risk in [1, 2, 3, 4, 5]:
    df[f'Percentage_{risk}%'] = df.apply(calculate_percentage, axis=1, risk=risk)

# Calculer le WinRate et les pourcentages pour chaque combinaison de 'StoplossSize', 'TradeRatio' par 'YearMonth'
def calculate_statistics(df, risk):
    df['Percentage'] = df[f'Percentage_{risk}%']
    monthly_results = df.groupby(['YearMonth', 'StoplossSize', 'TradeRatio']).agg(
        WinRate=('Result', lambda x: round((x == 'Winning').mean() * 100, 1)),
        TotalPercentage=('Percentage', lambda x: round(x.sum(), 1))
    ).unstack(level=[1, 2])
    return monthly_results

# Calculer les totaux globaux pour chaque stratégie
def calculate_global_statistics(df):
    global_results = df.groupby(['StoplossSize', 'TradeRatio']).agg(
        GlobalWinRate=('Result', lambda x: round((x == 'Winning').mean() * 100, 1)),
        GlobalTotalPercentage=('Percentage_1%', lambda x: round(x.sum(), 1))  # Utiliser le risque de 1% pour les totaux globaux
    ).reset_index()
    return global_results

# Définir le nom du fichier Excel
excel_file_name = f'{file_name}_Strategies_Trading_Data.xlsx'

# Utilisation de 'with' pour gérer automatiquement la fermeture et la sauvegarde
with pd.ExcelWriter(excel_file_name, engine='xlsxwriter') as writer:
    # Calculer les résultats pour différents niveaux de risque
    risks = [1, 2, 3, 4, 5]
    start_row = 0

    # Calculer les statistiques globales
    global_statistics = calculate_global_statistics(df)
    global_statistics.to_excel(writer, sheet_name='WinRate', startrow=0, index=False)

    # Isoler le WinRate dans un tableau
    winrate = calculate_statistics(df, 1).xs('WinRate', axis=1, level=0)
    winrate.to_excel(writer, sheet_name='WinRate', startrow=len(global_statistics) + 3)

    # Créer la feuille 'Results' avant de l'utiliser
    worksheet_results = writer.book.add_worksheet('Results')
    writer.sheets['Results'] = worksheet_results

    # Définir les formats de remplissage conditionnel
    format_green = writer.book.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
    format_red = writer.book.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

    for risk in risks:
        monthly_results = calculate_statistics(df, risk)
        total_percentage = monthly_results.xs('TotalPercentage', axis=1, level=0)

        # Écrire un titre pour le niveau de risque
        worksheet_results.write(start_row, 0, f'TotalPercentage {risk}% risk')
        start_row += 1

        # Écrire le TotalPercentage dans l'onglet 'Results'
        for r, (index, row) in enumerate(total_percentage.iterrows()):
            worksheet_results.write(start_row + r + 1, 0, str(index))
            for c, value in enumerate(row):
                if pd.notna(value):
                    worksheet_results.write(start_row + r + 1, c + 1, value)
                    if value >= 10:
                        worksheet_results.write(start_row + r + 1, c + 1, value, format_green)
                    else:
                        worksheet_results.write(start_row + r + 1, c + 1, value, format_red)

        start_row += len(total_percentage) + 3  # Laisser de l'espace de deux lignes entre les tableaux pour chaque niveau de risque

    # Grouper les données par 'StoplossSize' et 'TradeRatio'
    grouped = df.groupby(['StoplossSize', 'TradeRatio'])

    # Boucle sur chaque groupe pour créer un onglet par stratégie
    for (stoploss_size, trade_ratio), group in grouped:
        # Création d'un nom d'onglet en remplaçant les caractères non autorisés
        tab_name = f'Size_{stoploss_size}_Ratio_{trade_ratio}'.replace(':', '_')
        # Écrire les données du groupe dans un onglet spécifique du fichier Excel
        group.to_excel(writer, sheet_name=tab_name[:31], index=False)  # Nom de l'onglet limité à 31 caractères

# Fermer la connexion à la base de données
conn.close()
