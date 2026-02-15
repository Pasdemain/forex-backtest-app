import tkinter as tk
from tkinter import ttk
import pandas as pd
from tkinter import simpledialog
from datetime import datetime, timedelta, time
import os
from tkcalendar import Calendar
import sqlite3
import sys


# commande pour creer un executable
# pyinstaller --onefile --windowed ApplicationBacktest1.py

if getattr(sys, 'frozen', False):
    # Si l'application est empaquetée dans un exécutable
    application_path = os.path.dirname(sys.executable)
else:
    # Si l'application est exécutée comme un script Python (.py)
    application_path = os.path.dirname(os.path.abspath(__file__))

# Obtenez le chemin du répertoire où se trouve actuellement le script (ou l'exécutable)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construisez le chemin vers la base de données en utilisant un chemin relatif
#db_path = os.path.join(application_path, 'trading_data.db')

class DetailedNewsDialog(tk.Toplevel):
    def __init__(self, parent, news_name, date_limit, **kwargs):
        super().__init__(parent, **kwargs)
        self.title(f"More News Like '{news_name}'")
        self.geometry("1200x400")  # Taille de la fenêtre adaptée
        self.transient(parent)
        # Attendre que la fenêtre parente soit mise à jour pour obtenir ses dimensions et positions
        parent.update_idletasks()

        # Obtenir la position de la fenêtre parente
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()

        self.geometry(f"+{parent_x}+{parent_y}")

        # Création du Treeview avec des colonnes supplémentaires
        self.tree = ttk.Treeview(self, columns=("Time", "Impact", "Currency", "News", "Pips_Highest_Shadow", "Pips_Lowest_Shadow", "actual", "forecast", "previous"), show="headings")
        for col in self.tree['columns']:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(expand=True, fill=tk.BOTH)

        # Charger les données de la base de données
        self.load_data(news_name, date_limit)

        # Bouton de fermeture
        close_btn = ttk.Button(self, text="Close", command=self.destroy)
        close_btn.pack(pady=10)

    def load_data(self, news_name, date_limit):

        print(f"Chargement des données pour : {news_name}, avant le : {date_limit.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Connexion à la base de données
        print(f"Open Value: {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
       # Exécution de la requête SQL ajustée
        c.execute('''SELECT time, impact, currency, news, Pips_Highest_Shadow, Pips_Lowest_Shadow, actual, forecast, previous
                    FROM News
                    WHERE news = ? AND time < ?
                    ORDER BY time DESC''', (news_name, date_limit.strftime('%Y-%m-%d %H:%M:%S')))
        
        # Récupération des résultats
        rows = c.fetchall()
        
        # Affichage du nombre de lignes trouvées
        print(f"Nombre de lignes trouvées : {len(rows)}")
        
        if len(rows) > 0:
            # Si des lignes sont trouvées, les afficher
            for row in rows:
                print(f"Ligne : {row}")
                self.tree.insert('', tk.END, values=row)
        else:
            # Sinon, indiquer qu'aucune ligne n'a été trouvée
            print("Aucune donnée trouvée correspondant aux critères.")
        
        # Fermeture de la connexion
        conn.close()



class NewsDisplayDialog(tk.Toplevel):
    def __init__(self, parent, news_data, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("News Details")
        self.geometry("600x400")  # Taille de la fenêtre
        self.transient(parent)
        # Attendre que la fenêtre parente soit mise à jour pour obtenir ses dimensions et positions
        parent.update_idletasks()

        # Obtenir la position de la fenêtre parente
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()

        self.geometry(f"+{parent_x}+{parent_y}")

        # Création du Treeview
        self.tree = ttk.Treeview(self, columns=("Time", "Impact", "Currency", "News"), show="headings")
        self.tree.heading("Time", text="Time")
        self.tree.heading("Impact", text="Impact")
        self.tree.heading("Currency", text="Currency")
        self.tree.heading("News", text="News")

        # Configuration de la largeur des colonnes
        self.tree.column("Time", width=150)
        self.tree.column("Impact", width=100)
        self.tree.column("Currency", width=100)
        self.tree.column("News", width=250)

        # Insertion des données
        for news in news_data:
            self.tree.insert('', tk.END, values=(news[1], news[2], news[3], news[4]))

        self.tree.pack(expand=True, fill=tk.BOTH)

        # Associer un événement de double-clic sur une ligne à une méthode
        self.tree.bind("<Double-1>", self.on_item_double_click)

        # Bouton de fermeture
        close_btn = ttk.Button(self, text="Close", command=self.destroy)
        close_btn.pack(pady=10)


    def on_item_double_click(self, event):
        item_id = self.tree.selection()[0]
        item = self.tree.item(item_id)
        values = item['values']
        news_name = values[3]  # Assumons que 'News' est dans la 4ème colonne

        full_datetime_str = values[0]  
        # Conversion de la chaîne de caractères en objet datetime
        full_datetime = datetime.strptime(full_datetime_str, '%Y-%m-%d %H:%M:%S')

        # Ouvrir la fenêtre de détail avec les news similaires
        detailed_dialog = DetailedNewsDialog(self, news_name, full_datetime)
        detailed_dialog.transient(self.master)
        detailed_dialog.grab_set()



class NewEntryDialog(simpledialog.Dialog):

    def __init__(self, master, year, month, currency, db_path, **kwargs):
        self.year = year
        self.month = month
        self.currency = currency
        self.db_path = db_path

        super().__init__(master, **kwargs)


    def body(self, master):
        self.result = None
        # Utilisez self._set_body_widgets(master) pour ajouter des widgets à la boîte de dialogue
        self._set_body_widgets(master)
        self.attributes('-topmost', True)
        self.configure(bg='#FF99CC')

        self.after(100, self.position_window)  
        return master  # retourne l'élément qui doit avoir le focus initial

    
    def position_window(self):
        x_position = 120
        y_position = 120
        self.geometry(f"+{x_position}+{y_position}")

    def _set_body_widgets(self, master):
        current_row = 0
        
        # Day Selection
        ttk.Label(master, text="Day:").grid(column=0, row=current_row, sticky='w')
        self.day_var = tk.StringVar()
        self.select_day_btn = ttk.Button(master, text="Select Day", command=self._open_calendar)
        self.select_day_btn.grid(column=1, row=current_row, sticky='ew')
        self.selected_day_label = ttk.Label(master, text="")
        self.selected_day_label.grid(column=2, row=current_row, sticky='w')
        current_row += 1
        
        # Open Time
        ttk.Label(master, text="Open Time").grid(column=0, row=current_row, sticky='w')
        self.hour_var = tk.StringVar()
        # Génération des heures de 12:00 à 23:45
        hours = [f"{h:02d}:{m:02d}" for h in range(12, 24) for m in [0, 15, 30, 45]]
        self.hour_entry = ttk.Combobox(master, textvariable=self.hour_var, values=hours, width=5)
        self.hour_entry.grid(column=1, row=current_row, sticky='ew')
        
        # Bouton "Check News"
        self.check_news_btn = ttk.Button(master, text="Check News", command=self._check_news)
        self.check_news_btn.grid(column=2, row=current_row, sticky='w')

        # Checkbox for M5 timeframe (M15 by default)
        self.use_m5_var = tk.BooleanVar(value=False)  # False = M15 (default), True = M5
        self.m5_checkbox = ttk.Checkbutton(master, text="M5", variable=self.use_m5_var)
        self.m5_checkbox.grid(column=3, row=current_row, sticky='w')
        
        current_row += 1
        

        # Position
        ttk.Label(master, text="Position:").grid(column=0, row=current_row, sticky='w')
        self.position_var = tk.StringVar()
        ttk.Radiobutton(master, text="Sell", variable=self.position_var, value="Sell").grid(column=1, row=current_row, sticky='w')
        ttk.Radiobutton(master, text="Buy", variable=self.position_var, value="Buy").grid(column=2, row=current_row, sticky='w')
        current_row += 1

        # H4 Category
        ttk.Label(master, text="H4:").grid(column=0, row=current_row, sticky='w')
        self.h4_var = tk.StringVar()
        h4_options = ["Downtrend overall trend", "Downtrend because of break of structure", "Uptrend overall trend", "Uptrend because of break of structure"]
        self.h4_dropdown = ttk.Combobox(master, textvariable=self.h4_var, values=h4_options, width=40)
        self.h4_dropdown.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        self.h4_dropdown.bind("<<ComboboxSelected>>")  # Ajouter le bind ici
        current_row += 1


        # Catégorie H1
        ttk.Label(master, text="H1:").grid(column=0, row=current_row, sticky='w')
        self.h1_var = tk.StringVar()
        h1_options = ["Downtrend", "Uptrend", "Consolidate"]
        self.h1_dropdown = ttk.Combobox(master, textvariable=self.h1_var, values=h1_options, width=20)
        self.h1_dropdown.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        self.h1_dropdown.bind("<<ComboboxSelected>>")
        current_row += 1

        # Catégorie Entry Point
        ttk.Label(master, text="Confluence:").grid(column=0, row=current_row, sticky='w')
        self.entry_point_var = tk.StringVar()
        entry_point_options = [ "Order Block", "Extreme Order Block"]
        self.entry_point_dropdown = ttk.Combobox(master, textvariable=self.entry_point_var, values=entry_point_options, width=20)
        self.entry_point_dropdown.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        self.entry_point_dropdown.bind("<<ComboboxSelected>>")
        current_row += 1

        # Catégorie M15
        ttk.Label(master, text="M15:").grid(column=0, row=current_row, sticky='w')
        self.m15_var = tk.StringVar()
        m15_options = ["Break structure to downtrend", "Break structure to Uptrend"]
        self.m15_dropdown = ttk.Combobox(master, textvariable=self.m15_var, values=m15_options, width=30)
        self.m15_dropdown.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        self.m15_dropdown.bind("<<ComboboxSelected>>")
        current_row += 1



    def buttonbox(self):
        # Redéfinition de la création des boutons pour personnaliser leur comportement
        box = tk.Frame(self)

        # Bouton "AddEntry"
        add_entry_button = ttk.Button(box, text="AddEntry", width=10, command=self.calculate_data, default=tk.ACTIVE)
        add_entry_button.pack(side=tk.LEFT, padx=5, pady=5)

        
        # Bouton "Cancel"
        cancel_button = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        cancel_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.add_entry)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def calculate_data(self):
        # Session 
        # Convertit la chaîne de caractères self.hour_var en objet datetime.time
        input_time = datetime.strptime(self.hour_var.get(), "%H:%M").time()
        self.impact_news_var = ''
        
        # Vos définitions de départ
        london_start = time(15, 0)
        london_end = time(20, 0)
        new_york_start = time(20, 0)
        new_york_end = time(5, 0)
        tokyo_start = time(5, 0)
        tokyo_end = time(15, 0)

        # Supposons que input_time est déjà défini, par exemple:
        # input_time = datetime.strptime("04:00", "%H:%M").time()

        # Correction pour gérer la session de New York
        if london_start <= input_time < london_end:
            self.session_var = "London"
        elif tokyo_start <= input_time < tokyo_end:
            self.session_var = "Tokyo"
        elif new_york_start <= input_time or input_time < new_york_end:
            self.session_var = "New York"
        else:
            # Gère le cas où aucune condition n'est remplie, si nécessaire
            self.session_var = "Unknown"

        print(self.session_var)

        day_open = self.day_var.get()
        open_time = self.hour_var.get()
        format_str = '%d/%m/%y %H:%M'  # Le format attendu pour strptime
        start_datetime = datetime.strptime(f"{day_open} {open_time}", format_str)

        # Convertissez start_datetime au format de la base de données
        db_time_format = '%Y-%m-%d %H:%M:%S'
        db_time_str = start_datetime.strftime(db_time_format)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        print(f"Open Value: {self.currency}")

        # Détermine la table à utiliser en fonction du checkbox
        table_name = "candle_M5" if self.use_m5_var.get() else "candle_M15"

        # Utilisez db_time_str directement dans votre requête avec la table sélectionnée
        cursor.execute(f"SELECT open FROM {table_name} WHERE symbol = ? AND time = ?", (self.currency, db_time_str))
        result = cursor.fetchone()

        if result is not None:
            open_value = result[0]
            print(f"Open Value: {open_value}")
        else:
            # Gérez le cas où aucun résultat n'est trouvé, par exemple :
            open_value = None  # Ou une autre logique d'erreur appropriée
            print("Aucune donnée trouvée pour l'heure spécifiée.")
            return  # Sortie anticipée de la fonction si aucune donnée n'est trouvée


        stoploss_sizes = [35, 40, 45, 50, 55, 60 ]
        trade_ratios = [2, 3, 4, 5]
        position = self.position_var.get()


        currency_ratios = {
            "GBPJPY": 0.01,
            "GBPUSD": 0.0001,
            "EURUSD": 0.0001,
            "AUDUSD": 0.0001,
            "XAUUSD": 0.1, # Exemple, ajustez selon le besoin réel
            "EURJPY": 0.01, 
            "USDJPY": 0.01, 
            "EURGBP": 0.0001, 
            "EURAUD": 0.0001
        }
        ratiopips = currency_ratios.get(self.currency)


        for stoploss_size in stoploss_sizes:
            for ratio in trade_ratios:
                stoploss_price = stoploss_size * ratiopips

                if position == 'Buy':
                    take_profit_price = open_value + (stoploss_price * ratio)
                    stop_loss_price = open_value - stoploss_price
                else:  # Sell
                    take_profit_price = open_value - (stoploss_price * ratio)
                    stop_loss_price = open_value + stoploss_price

                print(f"Stoploss Size: {stoploss_size}, Ratio: {ratio}, Stoploss Price: {stoploss_price}, Open Value: {open_value}, Take Profit Price: {take_profit_price}, Stop Loss Price: {stop_loss_price}, Position: {position}, Currency: {self.currency}")
                # La requête SQL reste inchangée, elle est conçue pour fonctionner pour les deux types de positions.
                # La différence est dans la façon dont take_profit_price et stop_loss_price sont calculés ci-dessus.
                # Préparez la requête SQL sans LIMIT 1
                query = """
                    SELECT time, high, low
                    FROM candle_M15
                    WHERE symbol = ? AND time > ?
                    ORDER BY time ASC
                """
                cursor.execute(query, (self.currency, db_time_str))

                # Fetch all les résultats
                candles = cursor.fetchall()

                # Initialisation des variables pour la boucle
                found_result = False
                for candle in candles:
                    candle_time, high, low = candle
                    if position == 'Buy':
                        if high >= take_profit_price:
                            result_status = 'Winning'
                            found_result = True
                        elif low <= stop_loss_price:
                            result_status = 'Losing'
                            found_result = True
                    else:  # Sell
                        if low <= take_profit_price:
                            result_status = 'Winning'
                            found_result = True
                        elif high >= stop_loss_price:
                            result_status = 'Losing'
                            found_result = True

                    if found_result:
                        # Conversion du timestamp UNIX récupéré en datetime pour afficher
                        day_close_datetime = datetime.strptime(candle_time, '%Y-%m-%d %H:%M:%S')
                        
                        # Formatage de la date et de l'heure pour l'affichage
                        day_close_str = day_close_datetime.strftime('%d/%m/%y')
                        hour_close_str = day_close_datetime.strftime('%H:%M')

                        # Mise à jour des variables Tkinter avec les nouvelles valeurs
                        self.close_day_var = day_close_str  # Met à jour la variable de jour de fermeture
                        self.close_hour_var = hour_close_str  # Met à jour la variable d'heure de fermeture
                        self.result_var = result_status  # Met à jour le résultat du trade
                        self.stoploss_size_var = stoploss_size
                        self.trade_ratio_var = (f'1:{ratio}')


                        print(f"Result: {result_status} at {day_close_datetime}")
                        break  # Sortie de la boucle après avoir trouvé le résultat

                if not found_result:
                    # Si aucun résultat n'a été trouvé après avoir parcouru toutes les bougies
                    print("Aucun résultat déterminé après l'analyse de toutes les bougies disponibles.")
                self.add_entry()    

        conn.close()
        self.h4_var.set('')
        self.h1_var.set('')
        self.m15_var.set('')
        self.entry_point_var.set('')
        self.position_var.set('')

    def add_entry(self, event=None):
        # Récupération des valeurs pour la nouvelle entrée

        day_open = self.day_var.get()
        day_close = self.close_day_var
        open_time = self.hour_var.get()
        close_time = self.close_hour_var
        stoploss_size = self.stoploss_size_var
        trade_ratio = self.trade_ratio_var
        # Conversion des dates et des heures en datetime pour la concaténation
        format_str = '%d/%m/%y %H:%M'  # Le format attendu pour strptime
        start_datetime = datetime.strptime(f"{day_open} {open_time}", format_str)
        end_datetime = datetime.strptime(f"{day_close} {close_time}", format_str)
        # Format pour stockage dans SQLite (ISO 8601)
        start_datetime_str = start_datetime.strftime('%Y-%m-%d %H:%M')
        end_datetime_str = end_datetime.strftime('%Y-%m-%d %H:%M')
        
        # Affichage des valeurs pour vérification
        print(f"Open Time: {open_time}, Close Time: {close_time}, Stoploss Size: {stoploss_size}, day open: {day_open}, day close: {day_close}, Trade Ratio: {trade_ratio}")

        # Connexion à la base de données SQLite
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Compilation des résultats en un dictionnaire

        c.execute('''CREATE TABLE IF NOT EXISTS trading_entries
            (id INTEGER PRIMARY KEY, 
            day TEXT, 
            OpenTime TEXT, 
            ImpactPosition TEXT, 
            NewsTypes TEXT, 
            session TEXT, 
            position TEXT, 
            H4 TEXT, 
            H1 TEXT, 
            M15 TEXT, 
            EntryPoint TEXT, 
            StoplossSize INTEGER, 
            TradeRatio TEXT, 
            Closeday TEXT, 
            CloseTime TEXT, 
            Result TEXT,
            StartDatetime TEXT, 
            EndDatetime TEXT)''')

        
        c.execute('''SELECT * FROM trading_entries 
             WHERE StoplossSize = ? AND TradeRatio = ? 
             AND NOT (EndDatetime <= ? OR StartDatetime >= ?)''',
          (stoploss_size, trade_ratio, start_datetime_str, end_datetime_str))
        existing_entry = c.fetchone()

        # Affichage du résultat de la requête
        print(existing_entry)

        if existing_entry:
            tk.messagebox.showinfo("Entry Found", f"My love I found an existing entry already running for the following position. \n\nDetails:\n{existing_entry}")

        else:

            if hasattr(self, 'selected_options'):
                    # Concaténer les éléments sélectionnés en une chaîne de texte, séparés par une virgule
                    selected_news_types = ", ".join(self.selected_options)
            else:
                # Gérer le cas où aucune option n'a été sélectionnée ou _confirm_selection n'a pas encore été appelé
                selected_news_types = ''

            # Dictionnaire des champs à vérifier avec leur nom d'affichage correspondant
            fields_to_check = {
                "day": self.day_var.get(),
                "OpenTime": self.hour_var.get(),
                "session": self.session_var,
                "position": self.position_var.get(),
                "H4": self.h4_var.get(),
                "H1": self.h1_var.get(),
                "M15": self.m15_var.get(),
                "EntryPoint": self.entry_point_var.get(),
                "StoplossSize": self.stoploss_size_var,
                "TradeRatio": self.trade_ratio_var,
                "Closeday": self.close_day_var,
                "CloseTime": self.close_hour_var,
                "Result": self.result_var
            }

            # Vérification des champs
            missing_fields = [field_name for field_name, value in fields_to_check.items() if not value]
            if missing_fields:
                # Construction du message d'erreur avec chaque champ manquant sur une nouvelle ligne
                missing_fields_str = "\n".join(missing_fields)
                tk.messagebox.showwarning("Missing Information", f"I love you but you forget the following fields are missing or have a value of 0:\n{missing_fields_str}")
            else:

                # Updating self.result to include StartDatetime and EndDatetime
                self.result = {
                    "day": self.day_var.get(),
                    "OpenTime": self.hour_var.get(),
                    "ImpactPosition": self.impact_news_var,
                    "NewsTypes": selected_news_types,
                    "session": self.session_var,
                    "position": self.position_var.get(),
                    "H4": self.h4_var.get(),
                    "H1": self.h1_var.get(),
                    "M15": self.m15_var.get(),
                    "EntryPoint": self.entry_point_var.get(),
                    "StoplossSize": self.stoploss_size_var,
                    "TradeRatio": self.trade_ratio_var,
                    "Closeday": self.close_day_var,
                    "CloseTime": self.close_hour_var,
                    "Result": self.result_var,
                    "StartDatetime": start_datetime_str, 
                    "EndDatetime": end_datetime_str  
                }
                
                
                # Inserting data into the table, including the new fields
                c.execute('''INSERT INTO trading_entries
                    (day, OpenTime, ImpactPosition, NewsTypes, session, position, H4, H1, M15, EntryPoint, StoplossSize, TradeRatio, Closeday, CloseTime, Result, StartDatetime, EndDatetime)
                    VALUES (:day, :OpenTime, :ImpactPosition, :NewsTypes, :session, :position, :H4, :H1, :M15, :EntryPoint, :StoplossSize, :TradeRatio, :Closeday, :CloseTime, :Result, :StartDatetime, :EndDatetime)''', self.result)
                
                # Sauvegarde (commit) des changements
                conn.commit()
                
                # Fermeture de la connexion à la base de données
                conn.close()
                self.close_day_var = ''
                self.close_hour_var = ''
                self.trade_ratio_var = ''
                self.result_var = ''
        # Fermeture de la connexion à la base de données
        conn.close()
        

    def _open_calendar(self):
        self.cal_win = tk.Toplevel(self.master)
        self.cal_win.title("Select Day")
        self.cal_win.transient(self.master)  # Fait que la fenêtre soit toujours au-dessus de la fenêtre parente
        self.cal_win.grab_set()  # Rend la fenêtre modale

        cal_year = int(self.year)
        cal_month = int(self.month)
        
        self.cal = Calendar(self.cal_win, selectmode='day', year=cal_year, month=cal_month, day=1)
        self.cal.pack(padx=10, pady=10)

        ttk.Button(self.cal_win, text="Ok", command=self._confirm_date).pack()

        # Récupération de la position de NewEntryDialog
        dialog_x = self.winfo_x()
        dialog_y = self.winfo_y()

        # Attendre brièvement que la fenêtre soit rendue
        self.cal_win.update_idletasks()

        # Définition de la position de la fenêtre
        x_position = dialog_x + 30 # Position horizontale de la fenêtre
        y_position = dialog_y + 120 # Position verticale de la fenêtre
        self.cal_win.geometry(f"+{x_position}+{y_position}")

        self.cal_win.wait_window()  # Attend que la fenêtre du calendrier soit fermée



    def _confirm_date(self):
        # Récupération de la date sélectionnée depuis le calendrier
        selected_date = self.cal.get_date()
        print(selected_date)  # Pour vérifier le format de la date reçue
        # Conversion de la chaîne de date sélectionnée en objet datetime
        # Nous utilisons '%m/%d/%y' ici pour correspondre au format 'mm/dd/yy'
        try:
            selected_datetime = datetime.strptime(selected_date, '%m/%d/%y')  # Remplacement de '%Y' par '%y'
        except ValueError as e:
            print(f"Erreur lors de la conversion de la date: {e}")
            return  # Sortie précoce en cas d'erreur

        # Formatage de la date au format désiré 'jj/mm/aa'
        formatted_date = selected_datetime.strftime('%d/%m/%y')  # Format 'jj/mm/aa'
        # Mise à jour de la variable et de l'affichage avec la date formatée
        self.day_var.set(formatted_date)
        self.selected_day_label.config(text=formatted_date)
        self.cal_win.destroy()  # Ferme la fenêtre du calendrier


    def _check_news(self):
        # Extraire le jour, le mois et l'année depuis la date sélectionnée, en supposant le format 'jj/mm/aa'
        selected_day = self.day_var.get()  # Exemple : '15/06/23' pour le 15 Juin 2023
        day, month, year_suffix = selected_day.split('/')
        # Compléter l'année pour correspondre au format YYYY
        year = f"20{year_suffix}" if len(year_suffix) == 2 else year_suffix

        # Assurer le formatage à deux chiffres pour le mois et le jour
        month = f"{int(month):02d}"
        day = f"{int(day):02d}"

        # Extraire l'heure sélectionnée
        hour = self.hour_var.get()  # '07:15'

        # Composer la date et l'heure complètes dans le format attendu par datetime.strptime
        try:
            # Construction correcte de l'objet datetime en utilisant le format '%Y-%m-%d %H:%M'
            full_datetime = datetime.strptime(f"{year}-{month}-{day} {hour}", '%Y-%m-%d %H:%M')
            print("Date et heure sélectionnées :", full_datetime)
        except ValueError as e:
            print(f"Erreur lors de la conversion de la date: {e}")
            return  # Sortie précoce en cas d'erreur

        
        print("Date et heure sélectionnées 2 :", full_datetime)

        # Calcul des intervalles de temps pour la recherche
        time_before = full_datetime - timedelta(hours=6)
        time_after = full_datetime + timedelta(hours=200)

        # Connexion à la base de données SQLite
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Requête SQL pour trouver les nouvelles dans l'intervalle spécifié
        c.execute('''SELECT * FROM News 
                    WHERE time BETWEEN ? AND ?''', 
                (time_before.strftime('%Y-%m-%d %H:%M:%S'), time_after.strftime('%Y-%m-%d %H:%M:%S')))
        
        news_found = c.fetchall()


        if news_found:
            # Affichage des informations sur les nouvelles trouvées dans une nouvelle fenêtre
            news_display_dialog = NewsDisplayDialog(self, news_found)
            news_display_dialog.transient(self.master)  # Pour que la fenêtre soit toujours au-dessus de la fenêtre parente
            news_display_dialog.grab_set()  # Pour rendre la fenêtre modale
        else:
            tk.messagebox.showinfo("News Check", "No news found in the specified interval.", parent=self)


       
        
        # Fermeture de la connexion à la base de données
        conn.close()


    def apply(self):
        print("no more")


class TradingApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Trading Data Entry")
        
        self.year_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.currency_var = tk.StringVar()
        self._create_widgets()

    def _create_widgets(self):
        # Sélection de l'année
        ttk.Label(self.master, text="Year:").grid(column=0, row=0, sticky='w')
        year_entry = ttk.Combobox(self.master, textvariable=self.year_var, values=list(range(2024, 2028)))
        year_entry.grid(column=1, row=0, sticky='ew')
        
        # Sélection du mois
        ttk.Label(self.master, text="Month:").grid(column=0, row=1, sticky='w')
        month_entry = ttk.Combobox(self.master, textvariable=self.month_var, values=list(range(1, 13)))
        month_entry.grid(column=1, row=1, sticky='ew')

         # Sélection de la devise
        ttk.Label(self.master, text="Currency:").grid(column=0, row=2, sticky='w')
        currency_entry = ttk.Combobox(self.master, textvariable=self.currency_var, values=["GBPUSD", "GBPJPY", "XAUUSD", "EURUSD", "AUDUSD", "EURJPY", "USDJPY", "EURGBP", "EURAUD"])
        currency_entry.grid(column=1, row=2, sticky='ew')

        # Bouton pour nouvelle entrée
        new_entry_btn = tk.Button(self.master, text="New Entry", command=self._open_new_entry)
        new_entry_btn.grid(column=0, row=3, columnspan=2, sticky='ew', pady=5)

    def _open_new_entry(self):

        # Construction du chemin vers la base de données en utilisant la devise sélectionnée
        db_name = f"trading_data_{self.currency_var.get()}.db"
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name)

        dialog = NewEntryDialog(self.master, self.year_var.get(), self.month_var.get(), self.currency_var.get(), db_path=db_path)
        result = dialog.result
        print(result)  # Affiche le résultat pour le moment, à remplacer par la logique d'écriture Excel
        


def main():
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.configure(bg='#FF99CC')
    app = TradingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
