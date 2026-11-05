"""Interface : référence, puis 3 photos du textile, puis résultat."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageTk

import analyse
import memoire
import parametres

NOMBRE_PHOTOS = 3
PART_ROUGE_MINIMALE = 50  # en dessous, la référence est probablement une mauvaise photo
TYPES_IMAGES = [("Images", "*.jpg *.jpeg *.png")]
FICHIER_LOGO = Path(__file__).resolve().parent / "logo.png"

# Couleurs de l'interface
FOND = "#0d0506"
BARRE = "#080304"
CARTE = "#1a0b0d"
CARTE_CLAIRE = "#2a1215"
SURVOL = "#3d1a1e"
BORD = "#4a1c20"
ROUGE = "#e8283a"
ROUGE_SURVOL = "#f4515f"
ROUGE_SOMBRE = "#a3141e"
BLANC = "#f5f0f0"
GRIS = "#b3a5a6"

# Polices
POLICE = "Segoe UI"
TEXTE = (POLICE, 10)
TEXTE_GRAS = (POLICE, 10, "bold")
SOUS_TITRE = (POLICE, 12)
TITRE_CARTE = (POLICE, 12, "bold")
TITRE = (POLICE, 24, "bold")

# Animation de chargement (sa durée se règle dans les paramètres)
DELAI_IMAGE_MS = 30
PAUSE_FINALE_MS = 350
TAILLE_APERCU_SCAN = 150

ETAPES = ["La référence", "Les photos", "Le résultat"]

# Couleurs connues pour essayer la base RGB dans les paramètres
COULEURS_TEST = [
    ("Rouge", (255, 0, 0)),
    ("Rouge foncé", (139, 0, 0)),
    ("Rose", (255, 192, 203)),
    ("Rose vif", (255, 105, 180)),
    ("Rose très pâle", (235, 210, 224)),
    ("Blanc", (255, 255, 255)),
    ("Gris", (128, 128, 128)),
    ("Orange", (255, 165, 0)),
    ("Marron", (139, 69, 19)),
    ("Magenta", (255, 0, 255)),
]


def nombre(valeur):
    """Affiche 70.0 comme 70, et garde 72.5 tel quel."""
    return f"{valeur:g}"


def carte(parent):
    """Cadre sombre avec une bordure, utilisé pour chaque bloc de l'interface."""
    return tk.Frame(
        parent, bg=CARTE, padx=16, pady=14,
        highlightbackground=BORD, highlightcolor=BORD, highlightthickness=1,
    )


def texte(parent, contenu="", couleur=BLANC, police=TEXTE, fond=CARTE, **options):
    return tk.Label(parent, text=contenu, fg=couleur, bg=fond, font=police, **options)


def bouton(parent, contenu, commande, principal=False):
    """Bouton rouge (principal) ou sombre, qui s'éclaircit au survol."""
    fond = ROUGE if principal else CARTE_CLAIRE
    survol = ROUGE_SURVOL if principal else SURVOL

    element = tk.Button(
        parent, text=contenu, command=commande, bg=fond, fg=BLANC,
        activebackground=survol, activeforeground=BLANC,
        font=TEXTE_GRAS if principal else TEXTE,
        relief="flat", bd=0, padx=16, pady=8, cursor="hand2",
    )
    element.bind("<Enter>", lambda _: element.configure(bg=survol))
    element.bind("<Leave>", lambda _: element.configure(bg=fond))
    return element


def champ(parent, variable, largeur):
    return tk.Entry(
        parent, textvariable=variable, width=largeur, bg=CARTE_CLAIRE, fg=BLANC,
        insertbackground=BLANC, relief="flat", font=TEXTE,
        highlightthickness=1, highlightbackground=BORD, highlightcolor=ROUGE,
    )


def jauge(parent, valeur, fond=CARTE, taille=92):
    """Anneau qui se remplit selon le pourcentage, avec la valeur au centre."""
    dessin = tk.Canvas(parent, width=taille, height=taille, bg=fond, highlightthickness=0)
    marge = 8
    zone = (marge, marge, taille - marge, taille - marge)

    dessin.create_oval(*zone, outline=SURVOL, width=9)
    if valeur > 0:
        dessin.create_arc(
            *zone, start=90, extent=-min(valeur * 3.6, 359.9),
            style="arc", outline=ROUGE, width=9,
        )
    dessin.create_text(
        taille / 2, taille / 2, text=f"{valeur:.1f} %", fill=BLANC, font=(POLICE, 11, "bold")
    )
    return dessin


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RedBacteria : intensité du rouge")
        self.geometry("1120x780")
        self.minsize(1000, 730)
        self.configure(bg=FOND)
        self.configurer_style()

        parametres_valides = parametres.charger()

        # Étape 1
        self.mode = tk.StringVar(value="nouvelle")
        self.nom = tk.StringVar()
        self.nom_choisi = tk.StringVar()
        self.val_min = tk.StringVar(value=nombre(parametres.actuels["intervalle_min"]))
        self.val_max = tk.StringVar(value=nombre(parametres.actuels["intervalle_max"]))
        self.chemin_nouvelle = None
        self.references = {}
        self.reference = None

        # Étape 2
        self.photos = [None] * NOMBRE_PHOTOS

        # Chargement et résultat
        self.en_chargement = False
        self.resultats = []

        self.construire_barre()
        self.contenu = tk.Frame(self, bg=FOND)
        self.contenu.pack(side="left", fill="both", expand=True)

        self.page = None
        self.page_actuelle = self.afficher_etape_1
        self.afficher_etape_1()

        if not parametres_valides:
            messagebox.showerror(
                "Paramètres",
                "Le fichier parametres.json n'est pas valide : "
                "les valeurs par défaut sont utilisées.",
            )

    def configurer_style(self):
        """Thème sombre de la liste déroulante."""
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TCombobox", fieldbackground=CARTE_CLAIRE, background=CARTE_CLAIRE,
            foreground=BLANC, arrowcolor=BLANC, bordercolor=BORD,
            lightcolor=CARTE_CLAIRE, darkcolor=CARTE_CLAIRE, padding=5,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", CARTE_CLAIRE)],
            foreground=[("readonly", BLANC)],
            selectbackground=[("readonly", CARTE_CLAIRE)],
            selectforeground=[("readonly", BLANC)],
        )
        self.option_add("*TCombobox*Listbox.background", CARTE_CLAIRE)
        self.option_add("*TCombobox*Listbox.foreground", BLANC)
        self.option_add("*TCombobox*Listbox.selectBackground", ROUGE_SOMBRE)
        self.option_add("*TCombobox*Listbox.selectForeground", BLANC)

    def construire_barre(self):
        """Barre de gauche : le logo, le nom et les étapes."""
        barre = tk.Frame(
            self, bg=BARRE, width=220, highlightbackground=BORD, highlightthickness=1
        )
        barre.pack(side="left", fill="y")
        barre.pack_propagate(False)

        if FICHIER_LOGO.exists():
            with Image.open(FICHIER_LOGO) as image:
                self.icone = ImageTk.PhotoImage(image.copy())
                self.logo = ImageTk.PhotoImage(image.resize((120, 120), Image.LANCZOS))
            self.iconphoto(True, self.icone)
            tk.Label(barre, image=self.logo, bg=BARRE).pack(pady=(26, 8))

        nom = tk.Frame(barre, bg=BARRE)
        nom.pack(pady=(0, 26))
        for mot, couleur in (("Red", ROUGE), ("Bacteria", BLANC)):
            tk.Label(
                nom, text=mot, fg=couleur, bg=BARRE, font=(POLICE, 18, "bold"), padx=0, bd=0
            ).pack(side="left")

        self.menu = tk.Frame(barre, bg=BARRE)
        self.menu.pack(fill="x", padx=14)

        texte(
            barre, "Intensité du pigment\nrouge sur textile", GRIS, TEXTE, BARRE, justify="center"
        ).pack(side="bottom", pady=22)

        bouton(barre, "⚙   Paramètres", self.afficher_parametres).pack(
            side="bottom", fill="x", padx=14
        )

    def actualiser_menu(self, numero):
        """Met en avant l'étape en cours et coche les étapes terminées."""
        for element in self.menu.winfo_children():
            element.destroy()

        for i, nom in enumerate(ETAPES, start=1):
            active = i == numero
            marque = "✓" if i < numero else str(i)
            tk.Label(
                self.menu, text=f"{marque}    {nom}", anchor="w", padx=14, pady=10,
                bg=ROUGE_SOMBRE if active else BARRE,
                fg=BLANC if active or i < numero else GRIS,
                font=(POLICE, 11, "bold") if active else (POLICE, 11),
            ).pack(fill="x", pady=3)

    def nouvelle_page(self, numero, titre, titre_rouge, sous_titre):
        if self.page is not None:
            self.page.destroy()

        self.actualiser_menu(numero)
        self.page = tk.Frame(self.contenu, bg=FOND, padx=28, pady=20)
        self.page.pack(fill="both", expand=True)

        ligne = tk.Frame(self.page, bg=FOND)
        ligne.pack(anchor="w")
        texte(ligne, titre, BLANC, TITRE, FOND).pack(side="left")
        texte(ligne, titre_rouge, ROUGE, TITRE, FOND).pack(side="left")
        texte(self.page, sous_titre, GRIS, SOUS_TITRE, FOND).pack(anchor="w", pady=(0, 16))
        return self.page

    def afficher_vignette(self, label, chemin):
        """Affiche une petite version de la photo dans un label."""
        try:
            with Image.open(chemin) as image:
                image = image.convert("RGB")
                image.thumbnail((200, 200))
                vignette = ImageTk.PhotoImage(image)
        except OSError:
            label.configure(image="", text="Photo introuvable")
            label.image = None
            return

        label.configure(image=vignette, text="")
        label.image = vignette  # garde l'image en mémoire, sinon tkinter ne l'affiche pas

    # ----- Étape 1 : la référence -----

    def afficher_etape_1(self):
        self.page_actuelle = self.afficher_etape_1
        page = self.nouvelle_page(
            1, "Étape 1 : ", "la référence", "Choisissez une nouvelle photo ou une référence enregistrée."
        )

        try:
            self.references = memoire.charger_references()
        except ValueError:
            self.references = {}
            messagebox.showerror(
                "Mémoire illisible",
                "Le fichier references.json est illisible. "
                "Corrigez-le avant d'enregistrer une référence.",
            )

        boutons = tk.Frame(page, bg=FOND)
        boutons.pack(side="bottom", fill="x", pady=(16, 0))
        bouton(boutons, "Suivant  →", self.valider_etape_1, principal=True).pack(side="right")

        zone = tk.Frame(page, bg=FOND)
        zone.pack(fill="x", anchor="n")
        zone.columnconfigure(0, weight=3, uniform="etape1")
        zone.columnconfigure(1, weight=2, uniform="etape1")

        reglages = carte(zone)
        reglages.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        texte(reglages, "Source", police=TITRE_CARTE).pack(anchor="w", pady=(0, 10))

        choix = tk.Frame(reglages, bg=CARTE)
        choix.pack(anchor="w", pady=(0, 14))
        for contenu, valeur in (
            ("Nouvelle photo", "nouvelle"),
            ("Référence enregistrée", "enregistree"),
        ):
            tk.Radiobutton(
                choix, text=contenu, value=valeur, variable=self.mode, command=self.changer_mode,
                indicatoron=0, relief="flat", bd=0, padx=14, pady=7, cursor="hand2", font=TEXTE,
                bg=CARTE_CLAIRE, fg=BLANC, selectcolor=ROUGE_SOMBRE,
                activebackground=SURVOL, activeforeground=BLANC,
            ).pack(side="left", padx=(0, 6))

        self.zone_mode = tk.Frame(reglages, bg=CARTE)
        self.zone_mode.pack(fill="x", pady=(0, 18))

        texte(reglages, "Intervalle", police=TITRE_CARTE).pack(anchor="w", pady=(0, 8))
        intervalle = tk.Frame(reglages, bg=CARTE)
        intervalle.pack(anchor="w")
        texte(intervalle, "Min").pack(side="left")
        champ(intervalle, self.val_min, 6).pack(side="left", padx=6, ipady=4)
        texte(intervalle, "%     Max").pack(side="left")
        champ(intervalle, self.val_max, 6).pack(side="left", padx=6, ipady=4)
        texte(intervalle, "%").pack(side="left")
        texte(reglages, "En pourcentage de l'intensité de la référence.", GRIS).pack(
            anchor="w", pady=(8, 0)
        )

        cadre_apercu = carte(zone)
        cadre_apercu.grid(row=0, column=1, sticky="nsew")
        texte(cadre_apercu, "Aperçu", police=TITRE_CARTE).pack(anchor="w", pady=(0, 10))
        self.apercu = texte(cadre_apercu, "Aucune photo", GRIS)
        self.apercu.pack(expand=True)

        self.changer_mode()

    def changer_mode(self):
        for element in self.zone_mode.winfo_children():
            element.destroy()
        self.apercu.configure(image="", text="Aucune photo")
        self.apercu.image = None

        if self.mode.get() == "nouvelle":
            self.construire_nouvelle_photo()
        else:
            self.construire_reference_enregistree()

    def construire_nouvelle_photo(self):
        ligne = tk.Frame(self.zone_mode, bg=CARTE)
        ligne.pack(anchor="w", pady=(0, 12))
        bouton(ligne, "Choisir une photo...", self.choisir_reference).pack(side="left")
        self.label_chemin = texte(ligne, self.nom_de_photo(), GRIS)
        self.label_chemin.pack(side="left", padx=10)

        ligne = tk.Frame(self.zone_mode, bg=CARTE)
        ligne.pack(anchor="w")
        texte(ligne, "Nom (facultatif)").pack(side="left")
        champ(ligne, self.nom, 28).pack(side="left", padx=8, ipady=4)
        texte(self.zone_mode, "Sans nom, la référence n'est pas enregistrée.", GRIS).pack(
            anchor="w", pady=(6, 0)
        )

        if self.chemin_nouvelle:
            self.afficher_vignette(self.apercu, self.chemin_nouvelle)

    def nom_de_photo(self):
        return Path(self.chemin_nouvelle).name if self.chemin_nouvelle else "Aucune photo"

    def construire_reference_enregistree(self):
        if not self.references:
            texte(self.zone_mode, "Aucune référence enregistrée pour le moment.", GRIS).pack(
                anchor="w"
            )
            return

        noms = sorted(self.references)
        if self.nom_choisi.get() not in self.references:
            self.nom_choisi.set(noms[0])

        ligne = tk.Frame(self.zone_mode, bg=CARTE)
        ligne.pack(anchor="w")
        liste = ttk.Combobox(
            ligne, textvariable=self.nom_choisi, values=noms, state="readonly",
            width=22, font=TEXTE,
        )
        liste.pack(side="left")
        liste.bind("<<ComboboxSelected>>", lambda _: self.charger_reference_choisie())
        bouton(ligne, "Enregistrer l'intervalle", self.enregistrer_intervalle).pack(
            side="left", padx=8
        )

        self.charger_reference_choisie()

    def charger_reference_choisie(self):
        reference = self.references[self.nom_choisi.get()]
        self.val_min.set(nombre(reference["min"]))
        self.val_max.set(nombre(reference["max"]))
        self.afficher_vignette(self.apercu, memoire.chemin_photo(reference))

    def choisir_reference(self):
        chemin = filedialog.askopenfilename(title="Choisir la référence", filetypes=TYPES_IMAGES)
        if chemin:
            self.definir_nouvelle_photo(chemin)

    def definir_nouvelle_photo(self, chemin):
        self.chemin_nouvelle = chemin
        self.label_chemin.configure(text=self.nom_de_photo())
        self.afficher_vignette(self.apercu, chemin)

    def lire_intervalle(self):
        """Renvoie (min, max), ou None après avoir affiché une erreur."""
        try:
            minimum = float(self.val_min.get().replace(",", "."))
            maximum = float(self.val_max.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Intervalle", "Le minimum et le maximum doivent être des nombres.")
            return None

        if not 0 <= minimum < maximum:
            messagebox.showerror(
                "Intervalle", "Le minimum doit être positif et plus petit que le maximum."
            )
            return None

        return minimum, maximum

    def enregistrer_intervalle(self):
        intervalle = self.lire_intervalle()
        if intervalle is None:
            return

        nom = self.nom_choisi.get()
        memoire.modifier_intervalle(nom, *intervalle)
        self.references = memoire.charger_references()
        messagebox.showinfo("Référence", f"Intervalle enregistré pour « {nom} ».")

    def valider_etape_1(self):
        intervalle = self.lire_intervalle()
        if intervalle is None:
            return

        if self.mode.get() == "nouvelle":
            reference = self.preparer_nouvelle_reference(*intervalle)
        else:
            reference = self.preparer_reference_enregistree(*intervalle)

        if reference is not None:
            self.reference = reference
            self.photos = [None] * NOMBRE_PHOTOS
            self.afficher_etape_2()

    def preparer_reference_enregistree(self, minimum, maximum):
        nom = self.nom_choisi.get()
        if nom not in self.references:
            messagebox.showerror("Référence", "Choisissez d'abord une référence.")
            return None

        reference = self.references[nom]
        try:
            # Recalculée pour rester exacte si la taille de la matrice a changé
            matrice = analyse.charger_matrice(memoire.chemin_photo(reference))
            rougeur = analyse.rougeur_reference(matrice)
        except OSError:
            rougeur = reference["rougeur"]
        else:
            if not self.confirmer_part_de_rouge(matrice):
                return None

        return {"nom": nom, "rougeur": rougeur, "min": minimum, "max": maximum}

    def confirmer_part_de_rouge(self, matrice):
        """Demande confirmation si la base RGB rejette une grande partie de la référence."""
        part = analyse.part_de_rouge(matrice)
        return part >= PART_ROUGE_MINIMALE or messagebox.askyesno(
            "Référence",
            f"Seulement {part:.0f} % de cette photo est rouge ou rose. Continuer quand même ?",
        )

    def preparer_nouvelle_reference(self, minimum, maximum):
        if not self.chemin_nouvelle:
            messagebox.showerror("Référence", "Choisissez d'abord une photo.")
            return None

        try:
            matrice = analyse.charger_matrice(self.chemin_nouvelle)
        except OSError:
            messagebox.showerror("Référence", "Cette photo ne peut pas être ouverte.")
            return None

        rougeur = analyse.rougeur_reference(matrice)
        if rougeur <= 0:
            messagebox.showerror("Référence", "Cette photo ne contient pas de rouge.")
            return None

        if not self.confirmer_part_de_rouge(matrice):
            return None

        nom = self.nom.get().strip()
        if nom:
            if nom in self.references and not messagebox.askyesno(
                "Référence", f"La référence « {nom} » existe déjà. La remplacer ?"
            ):
                return None
            memoire.enregistrer_reference(nom, self.chemin_nouvelle, rougeur, minimum, maximum)

        return {"nom": nom or "non enregistrée", "rougeur": rougeur, "min": minimum, "max": maximum}

    # ----- Étape 2 : les photos du textile -----

    def afficher_etape_2(self):
        self.page_actuelle = self.afficher_etape_2
        page = self.nouvelle_page(
            2, "Étape 2 : ", f"les {NOMBRE_PHOTOS} photos",
            f"Référence : {self.reference['nom']}",
        )

        boutons = tk.Frame(page, bg=FOND)
        boutons.pack(side="bottom", fill="x", pady=(16, 0))
        bouton(boutons, "←  Retour", self.afficher_etape_1).pack(side="left")
        bouton(boutons, "Voir le résultat  →", self.valider_etape_2, principal=True).pack(
            side="right"
        )

        zone = tk.Frame(page, bg=FOND)
        zone.pack(fill="x", anchor="n")
        self.colonnes = []

        for i in range(NOMBRE_PHOTOS):
            zone.columnconfigure(i, weight=1, uniform="photos")
            colonne = carte(zone)
            colonne.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            texte(colonne, f"Photo {i + 1}", police=TITRE_CARTE).pack(pady=(0, 10))

            cadre = tk.Frame(colonne, bg=CARTE, height=210)
            cadre.pack(fill="x", pady=(0, 12))
            cadre.pack_propagate(False)
            colonne.vignette = texte(cadre, "Aucune photo", GRIS)
            colonne.vignette.pack(expand=True)
            if self.photos[i]:
                self.afficher_vignette(colonne.vignette, self.photos[i]["chemin"])

            bouton(colonne, "Choisir...", lambda i=i: self.choisir_photo(i)).pack()
            self.colonnes.append(colonne)

    def choisir_photo(self, i):
        chemin = filedialog.askopenfilename(
            title=f"Choisir la photo {i + 1}", filetypes=TYPES_IMAGES
        )
        if chemin:
            self.definir_photo(i, chemin)

    def definir_photo(self, i, chemin):
        try:
            matrice = analyse.charger_matrice(chemin)
        except OSError:
            messagebox.showerror("Photo", "Cette photo ne peut pas être ouverte.")
            return

        self.photos[i] = {"chemin": chemin, "matrice": matrice}
        self.afficher_vignette(self.colonnes[i].vignette, chemin)

    def valider_etape_2(self):
        if None in self.photos:
            messagebox.showerror("Photos", f"Choisissez les {NOMBRE_PHOTOS} photos.")
            return

        self.afficher_chargement()

    # ----- Chargement : animation avant le résultat -----

    def afficher_chargement(self):
        self.en_chargement = True
        self.resultats = []
        page = self.nouvelle_page(
            3, "Analyse ", "en cours", f"Comparaison avec la référence : {self.reference['nom']}"
        )

        centre = tk.Frame(page, bg=FOND)
        centre.pack(expand=True)

        # Anneau de progression, avec un petit arc qui tourne à l'intérieur
        taille = 190
        self.anneau = tk.Canvas(centre, width=taille, height=taille, bg=FOND, highlightthickness=0)
        self.anneau.pack(pady=(0, 10))
        self.anneau.create_oval(12, 12, taille - 12, taille - 12, outline=SURVOL, width=14)
        self.arc_progression = self.anneau.create_arc(
            12, 12, taille - 12, taille - 12, start=90, extent=0,
            style="arc", outline=ROUGE, width=14,
        )
        self.arc_rotation = self.anneau.create_arc(
            32, 32, taille - 32, taille - 32, start=90, extent=70,
            style="arc", outline=ROUGE_SOMBRE, width=4,
        )
        self.texte_progression = self.anneau.create_text(
            taille / 2, taille / 2, text="0 %", fill=BLANC, font=(POLICE, 22, "bold")
        )

        self.texte_statut = texte(centre, "", GRIS, SOUS_TITRE, FOND)
        self.texte_statut.pack(pady=(0, 20))

        rangee = tk.Frame(centre, bg=FOND)
        rangee.pack()
        self.scans = [self.construire_scan(rangee, i) for i in range(NOMBRE_PHOTOS)]

        self.animer_chargement(0)

    def construire_scan(self, parent, i):
        """Miniature de la photo, assombrie jusqu'au passage de la ligne de scan."""
        cadre = carte(parent)
        cadre.configure(padx=10, pady=10)
        cadre.pack(side="left", padx=8)

        taille = TAILLE_APERCU_SCAN
        image = Image.fromarray(np.rint(self.photos[i]["matrice"]).astype(np.uint8))
        miniature = ImageTk.PhotoImage(image.resize((taille, taille), Image.BILINEAR))

        dessin = tk.Canvas(cadre, width=taille, height=taille, bg=CARTE, highlightthickness=0)
        dessin.image = miniature  # garde l'image en mémoire, sinon tkinter ne l'affiche pas
        dessin.create_image(0, 0, image=miniature, anchor="nw")
        voile = dessin.create_rectangle(
            0, 0, taille, taille, fill=FOND, outline="", stipple="gray75"
        )
        ligne = dessin.create_line(0, 0, taille, 0, fill=ROUGE, width=3, state="hidden")
        dessin.pack()

        statut = texte(cadre, f"Photo {i + 1}", GRIS)
        statut.pack(pady=(8, 0))
        return {"dessin": dessin, "voile": voile, "ligne": ligne, "statut": statut}

    def animer_chargement(self, image):
        duree_ms = parametres.actuels["duree_scan"] * 1000
        images_par_photo = max(1, round(duree_ms / DELAI_IMAGE_MS))
        total = images_par_photo * NOMBRE_PHOTOS
        progression = image / total
        self.anneau.itemconfigure(self.arc_progression, extent=-359.9 * progression)
        self.anneau.itemconfigure(self.arc_rotation, start=(90 - image * 14) % 360)
        self.anneau.itemconfigure(self.texte_progression, text=f"{progression * 100:.0f} %")

        # Une photo vient d'être entièrement parcourue : on calcule son résultat
        if image > 0 and image % images_par_photo == 0:
            self.terminer_scan(image // images_par_photo - 1)

        if image >= total:
            self.texte_statut.configure(text="Analyse terminée")
            self.after(PAUSE_FINALE_MS, self.afficher_etape_3)
            return

        self.deplacer_scan(image // images_par_photo, image % images_par_photo / images_par_photo)
        self.after(DELAI_IMAGE_MS, self.animer_chargement, image + 1)

    def deplacer_scan(self, i, avancement):
        scan = self.scans[i]
        taille = TAILLE_APERCU_SCAN
        y = taille * avancement

        scan["dessin"].itemconfigure(scan["ligne"], state="normal")
        scan["dessin"].coords(scan["ligne"], 0, y, taille, y)
        scan["dessin"].coords(scan["voile"], 0, y, taille, taille)
        scan["statut"].configure(text="Analyse...", fg=BLANC)
        self.texte_statut.configure(text=f"Analyse de la photo {i + 1} sur {NOMBRE_PHOTOS}")

    def terminer_scan(self, i):
        reference = self.reference
        self.resultats.append(
            analyse.analyser_photo(
                self.photos[i]["matrice"], reference["rougeur"], reference["min"], reference["max"]
            )
        )

        scan = self.scans[i]
        scan["dessin"].itemconfigure(scan["ligne"], state="hidden")
        scan["dessin"].itemconfigure(scan["voile"], state="hidden")
        scan["statut"].configure(text=f"✓  Photo {i + 1}", fg=BLANC)

    # ----- Étape 3 : le résultat -----

    def afficher_etape_3(self):
        self.en_chargement = False
        self.page_actuelle = self.afficher_etape_3
        reference = self.reference
        page = self.nouvelle_page(
            3, "Étape 3 : ", "le résultat",
            f"Référence : {reference['nom']}   |   Intervalle : "
            f"{nombre(reference['min'])} à {nombre(reference['max'])} %",
        )
        resultats = self.resultats

        self.construire_intensites(page, resultats)

        boutons = tk.Frame(page, bg=FOND)
        boutons.pack(side="bottom", fill="x", pady=(12, 0))
        bouton(boutons, "←  Changer de référence", self.afficher_etape_1).pack(side="left")
        bouton(boutons, "Nouvelles photos", self.recommencer_photos, principal=True).pack(
            side="right"
        )

        self.construire_figure(page, resultats)

    def construire_intensites(self, page, resultats):
        """Une carte avec une jauge par photo."""
        zone = tk.Frame(page, bg=FOND)
        zone.pack(fill="x", pady=(0, 12))

        for i, resultat in enumerate(resultats):
            zone.columnconfigure(i, weight=1, uniform="intensites")
            cadre = carte(zone)
            cadre.configure(padx=10, pady=8)
            cadre.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            jauge(cadre, resultat["intensite"]).pack(side="left", padx=(0, 10))
            libelles = tk.Frame(cadre, bg=CARTE)
            libelles.pack(side="left")
            texte(libelles, f"Photo {i + 1}", police=TITRE_CARTE).pack(anchor="w")
            texte(libelles, "Intensité", GRIS).pack(anchor="w")

    def construire_figure(self, page, resultats):
        cadre = carte(page)
        cadre.configure(padx=8, pady=8)
        cadre.pack(fill="both", expand=True)
        texte(cadre, "Part de blanc = intensité     Blanc : cases les plus intenses     Noir : le reste ou hors intervalle", GRIS).pack(
            side="bottom", pady=(4, 0)
        )

        figure = Figure(figsize=(8, 3.7), dpi=100, facecolor=CARTE)
        axes = figure.subplots(2, NOMBRE_PHOTOS)

        for i, (photo, resultat) in enumerate(zip(self.photos, resultats)):
            axes[0][i].imshow(
                np.rint(photo["matrice"]).astype(np.uint8), interpolation="nearest"
            )
            axes[0][i].set_title(f"Photo {i + 1}", fontsize=10, color=BLANC)
            axes[1][i].imshow(
                resultat["matrice_01"], cmap="gray", vmin=0, vmax=1, interpolation="nearest"
            )
            axes[1][i].set_title("Matrice", fontsize=10, color=BLANC)

            # Photo sans cadre ; matrice avec cadre, pour la voir même si elle est toute noire
            axes[0][i].axis("off")
            axes[1][i].set_xticks([])
            axes[1][i].set_yticks([])
            for bord in axes[1][i].spines.values():
                bord.set_color(GRIS)

        figure.tight_layout()
        canvas = FigureCanvasTkAgg(figure, master=cadre)
        canvas.draw()
        canvas.get_tk_widget().configure(bg=CARTE, highlightthickness=0)
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def recommencer_photos(self):
        self.photos = [None] * NOMBRE_PHOTOS
        self.afficher_etape_2()

    # ----- Paramètres -----

    def afficher_parametres(self):
        if self.en_chargement:
            return  # l'animation a besoin de sa page jusqu'à la fin

        page = self.nouvelle_page(
            0, "Les ", "paramètres", "Modifiez les réglages de l'analyse, puis appliquez-les."
        )

        self.vars_parametres = {
            cle: tk.StringVar(value=nombre(valeur))
            for cle, valeur in parametres.actuels.items()
            if cle != "taille_bloc"
        }
        self.var_bloc = tk.IntVar(value=parametres.actuels["taille_bloc"])

        boutons = tk.Frame(page, bg=FOND)
        boutons.pack(side="bottom", fill="x", pady=(14, 0))
        bouton(boutons, "Valeurs par défaut", self.remettre_defauts).pack(side="left")
        bouton(boutons, "Appliquer", self.appliquer_parametres, principal=True).pack(side="right")
        bouton(boutons, "Annuler", self.page_actuelle).pack(side="right", padx=8)

        zone = tk.Frame(page, bg=FOND)
        zone.pack(fill="x", anchor="n")
        zone.columnconfigure(0, weight=3, uniform="parametres")
        zone.columnconfigure(1, weight=2, uniform="parametres")

        self.construire_base_rgb(zone)
        self.construire_analyse(zone)
        self.construire_test_couleurs(zone)

        for variable in self.vars_parametres.values():
            variable.trace_add("write", lambda *_: self.actualiser_test_couleurs())
        self.actualiser_test_couleurs()

    def ligne_reglage(self, parent, ligne, cle, nom, aide):
        texte(parent, nom).grid(row=ligne, column=0, sticky="w", pady=4)
        champ(parent, self.vars_parametres[cle], 7).grid(
            row=ligne, column=1, padx=10, pady=4, ipady=3
        )
        texte(parent, aide, GRIS).grid(row=ligne, column=2, sticky="w", pady=4)

    def construire_base_rgb(self, zone):
        cadre = carte(zone)
        cadre.grid(row=0, column=0, sticky="nsew", padx=(0, 14), pady=(0, 12))
        texte(cadre, "Base RGB : ce qui compte comme rouge", police=TITRE_CARTE).pack(
            anchor="w", pady=(0, 8)
        )

        lignes = tk.Frame(cadre, bg=CARTE)
        lignes.pack(anchor="w")
        self.ligne_reglage(lignes, 0, "r_min", "R minimum", "Rejette le presque noir")
        self.ligne_reglage(lignes, 1, "rougeur_min", "Rougeur minimum", "Rejette blanc et gris")
        self.ligne_reglage(lignes, 2, "g_moins_b_max", "G - B maximum", "Rejette orange et marron")
        self.ligne_reglage(lignes, 3, "b_moins_g_max", "B - G maximum", "Rejette violet et magenta")
        texte(cadre, "Rougeur = R - max(G, B)", GRIS).pack(anchor="w", pady=(6, 0))

    def construire_analyse(self, zone):
        cadre = carte(zone)
        cadre.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        texte(cadre, "Analyse", police=TITRE_CARTE).pack(anchor="w", pady=(0, 8))

        texte(cadre, "Taille de la matrice").pack(anchor="w")
        choix = tk.Frame(cadre, bg=CARTE)
        choix.pack(anchor="w", pady=(4, 2))
        for taille in parametres.TAILLES_BLOC:
            cases = analyse.TAILLE_IMAGE // taille
            tk.Radiobutton(
                choix, text=f"{cases} x {cases}", value=taille, variable=self.var_bloc,
                indicatoron=0, relief="flat", bd=0, padx=12, pady=6, cursor="hand2", font=TEXTE,
                bg=CARTE_CLAIRE, fg=BLANC, selectcolor=ROUGE_SOMBRE,
                activebackground=SURVOL, activeforeground=BLANC,
            ).pack(side="left", padx=(0, 6))
        texte(cadre, "Plus de cases : plus de détails, mais plus sensible au bruit.", GRIS).pack(
            anchor="w", pady=(0, 8)
        )

        lignes = tk.Frame(cadre, bg=CARTE)
        lignes.pack(anchor="w")
        self.ligne_reglage(lignes, 0, "intervalle_min", "Intervalle min", "% proposé à l'étape 1")
        self.ligne_reglage(lignes, 1, "intervalle_max", "Intervalle max", "% proposé à l'étape 1")
        self.ligne_reglage(lignes, 2, "duree_scan", "Animation", "secondes par photo")

    def construire_test_couleurs(self, zone):
        cadre = carte(zone)
        cadre.grid(row=0, column=1, rowspan=2, sticky="nsew")
        texte(cadre, "Test de la base RGB", police=TITRE_CARTE).pack(anchor="w")
        texte(cadre, "Mis à jour pendant la saisie.", GRIS).pack(anchor="w", pady=(0, 8))

        self.tests_couleurs = []
        for nom, (r, g, b) in COULEURS_TEST:
            ligne = tk.Frame(cadre, bg=CARTE)
            ligne.pack(fill="x", pady=3)
            tk.Frame(
                ligne, bg=f"#{r:02x}{g:02x}{b:02x}", width=22, height=22,
                highlightbackground=BORD, highlightthickness=1,
            ).pack(side="left", padx=(0, 10))
            texte(ligne, nom).pack(side="left")
            resultat = texte(ligne, "")
            resultat.pack(side="right")
            self.tests_couleurs.append(((r, g, b), resultat))

    def lire_parametres(self):
        """Renvoie les valeurs saisies. Lève une ValueError si un nombre n'est pas valide."""
        valeurs = {"taille_bloc": self.var_bloc.get()}

        for cle, variable in self.vars_parametres.items():
            saisie = variable.get().replace(",", ".")
            if cle in ("r_min", "rougeur_min", "g_moins_b_max", "b_moins_g_max"):
                try:
                    valeurs[cle] = int(saisie)
                except ValueError:
                    raise ValueError("Les valeurs RGB doivent être des nombres entiers.") from None
            else:
                try:
                    valeurs[cle] = float(saisie)
                except ValueError:
                    raise ValueError(
                        "L'intervalle et la durée de l'animation doivent être des nombres."
                    ) from None

        return valeurs

    def actualiser_test_couleurs(self):
        try:
            valeurs = self.lire_parametres()
            parametres.verifier(valeurs)
        except ValueError:
            for _, resultat in self.tests_couleurs:
                resultat.configure(text="–", fg=GRIS)
            return

        for couleur, resultat in self.tests_couleurs:
            matrice = np.array([[couleur]], dtype=float)
            if analyse.est_rouge(matrice, valeurs)[0, 0]:
                resultat.configure(text="✓  Accepté", fg=BLANC)
            else:
                resultat.configure(text="✕  Rejeté", fg=GRIS)

    def remettre_defauts(self):
        self.var_bloc.set(parametres.DEFAUTS["taille_bloc"])
        for cle, variable in self.vars_parametres.items():
            variable.set(nombre(parametres.DEFAUTS[cle]))

    def appliquer_parametres(self):
        avant = (parametres.actuels["intervalle_min"], parametres.actuels["intervalle_max"])

        try:
            parametres.enregistrer(self.lire_parametres())
        except (ValueError, OSError) as erreur:
            messagebox.showerror("Paramètres", str(erreur))
            return

        apres = (parametres.actuels["intervalle_min"], parametres.actuels["intervalle_max"])
        if apres != avant:
            self.val_min.set(nombre(apres[0]))
            self.val_max.set(nombre(apres[1]))

        # Les photos déjà choisies ont été calculées avec les anciens réglages
        self.afficher_etape_1()


if __name__ == "__main__":
    Application().mainloop()
