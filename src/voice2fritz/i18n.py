"""UI translations. English is the source language; tr() looks up the German text.

Placeholders use str.format names, e.g. tr("Name for {number}:", number=number).
"""

LANGUAGES = {"en": "English", "de": "Deutsch"}
DEFAULT_LANGUAGE = "en"

_GERMAN = {
    # Main window
    "Backspace": "Rücktaste",
    "📞 CALL": "📞 ANRUFEN",
    "✕ HANGUP": "✕ AUFLEGEN",
    "Call": "Anrufen",
    "✕ Hangup": "✕ Auflegen",
    "Hang up": "Auflegen",
    "🔇 Mute": "🔇 Stumm",
    "Mute": "Stummschalten",
    "Not registered": "Nicht angemeldet",
    "Show voice2fritz": "voice2fritz anzeigen",
    "Quit": "Beenden",
    "Close voice2fritz?": "voice2fritz schließen?",
    "Quit voice2fritz, or keep it running in the tray?": "voice2fritz beenden oder im Infobereich weiterlaufen lassen?",
    "Minimize to Tray": "In den Infobereich",
    "Cancel": "Abbrechen",
    "Settings verified": "Einstellungen geprüft",
    "The new settings work: registered as {account}.": "Die neuen Einstellungen funktionieren: angemeldet als {account}.",
    "Could not register with the new settings. Check host, username and password.":
        "Anmeldung mit den neuen Einstellungen fehlgeschlagen. Bitte Host, Benutzername und Passwort prüfen.",
    "Could not register with the saved settings. Check host, username and password.":
        "Anmeldung mit den gespeicherten Einstellungen fehlgeschlagen. Bitte Host, Benutzername und Passwort prüfen.",
    "Registration failed for {account}: {detail}": "Anmeldung für {account} fehlgeschlagen: {detail}",
    "No response from the registrar for {account}.": "Keine Antwort von der FRITZ!Box für {account}.",
    "The FRITZ!Box rejected the login. Check the username and password in Settings.":
        "Die FRITZ!Box hat die Anmeldung abgelehnt. Bitte Benutzername und Passwort in den Einstellungen prüfen.",
    "SIP registration failed": "SIP-Anmeldung fehlgeschlagen",
    "Open Settings": "Einstellungen öffnen",
    "Authorization failed for {account}: {detail}": "Autorisierung für {account} fehlgeschlagen: {detail}",
    "Restart required": "Neustart erforderlich",
    "The language changes after a restart. Restart voice2fritz now?":
        "Die Sprache wird nach einem Neustart umgestellt. voice2fritz jetzt neu starten?",
    "Restart now": "Jetzt neu starten",
    "Later": "Später",
    "Your system language is {language}. Switch voice2fritz to {language}?":
        "Deine Systemsprache ist {language}. voice2fritz auf {language} umstellen?",
    "You can change this later in Settings.": "Das lässt sich später in den Einstellungen ändern.",
    "Switch to {language}": "Auf {language} umstellen",
    "Keep {language}": "{language} beibehalten",
    # Navigation
    "Dialpad": "Wähltastatur",
    "Contacts": "Kontakte",
    "Call Log": "Anrufliste",
    "Settings": "Einstellungen",
    # Call details and call states (PJSIP state names)
    "Active": "Aktiv",
    "No active call": "Kein aktiver Anruf",
    "CALLING": "Wählt…",
    "INCOMING": "Eingehend",
    "EARLY": "Klingelt",
    "CONNECTING": "Verbinde…",
    "CONFIRMED": "Verbunden",
    "DISCONNCTD": "Beendet",
    # Incoming call popup
    "Incoming call": "Eingehender Anruf",
    "📞 Answer": "📞 Annehmen",
    "✕ Decline": "✕ Ablehnen",
    # Call log
    "Clear": "Leeren",
    "Redial": "Erneut wählen",
    "Call back": "Zurückrufen",
    "Save to contacts…": "In Kontakte speichern…",
    "Save to contacts": "In Kontakte speichern",
    "Name for {number}:": "Name für {number}:",
    "Edit": "Bearbeiten",
    "Edit the number on the dialpad before calling": "Nummer vor dem Anruf auf der Wähltastatur bearbeiten",
    # Contacts
    "Name": "Name",
    "Type": "Typ",
    "Number": "Nummer",
    "Sort by:": "Sortieren nach:",
    "Add contact": "Kontakt hinzufügen",
    "Type (optional)": "Typ (optional)",
    "Add": "Hinzufügen",
    "Delete": "Löschen",
    "Select": "Auswählen",
    "Sync Google": "Google synchronisieren",
    "{count} contact(s) added or updated.": "{count} Kontakt(e) hinzugefügt oder aktualisiert.",
    "Could not sync Google contacts: {message}": "Google-Kontakte konnten nicht synchronisiert werden: {message}",
    # Settings
    "FRITZ!Box Account": "FRITZ!Box-Konto",
    "Host": "Host",
    "Username": "Benutzername",
    "Password": "Passwort",
    "No password saved": "Kein Passwort gespeichert",
    "Password tested and working": "Passwort getestet und funktioniert",
    "Saved password was rejected - enter it again": "Gespeichertes Passwort wurde abgelehnt - bitte neu eingeben",
    "Password saved (not tested yet)": "Passwort gespeichert (noch nicht getestet)",
    "Mic": "Mikrofon",
    "Mic level": "Mikrofonpegel",
    "Speaker": "Lautsprecher",
    "Audio test": "Audiotest",
    "Call audio IP": "IP für Anrufton",
    "Language": "Sprache",
    "Save": "Speichern",
    "Setup wizard...": "Einrichtungsassistent...",
    "Google sync overwrites local contacts with the same name":
        "Google-Synchronisierung überschreibt lokale Kontakte mit gleichem Namen",
    "Live microphone level": "Aktueller Mikrofonpegel",
    "Test mic && speaker": "Mikrofon && Lautsprecher testen",
    "Records 3 seconds, then plays them back.": "Nimmt 3 Sekunden auf und spielt sie dann ab.",
    "Not registered yet": "Noch nicht angemeldet",
    "Call audio goes through the VPN; the FRITZ!Box may not reach it.":
        "Der Anrufton läuft über das VPN; die FRITZ!Box erreicht ihn eventuell nicht.",
    "Local address the FRITZ!Box sends call audio to.": "Lokale Adresse, an die die FRITZ!Box den Anrufton sendet.",
    "Not available during a call": "Während eines Anrufs nicht verfügbar",
    "Recording - speak now...": "Aufnahme läuft - bitte jetzt sprechen...",
    "Preparing playback...": "Wiedergabe wird vorbereitet...",
    "Test failed: the recording was not saved.": "Test fehlgeschlagen: Die Aufnahme wurde nicht gespeichert.",
    "Recorded only silence - is the mic muted?": "Nur Stille aufgenommen - ist das Mikrofon stummgeschaltet?",
    "Playing back...": "Wiedergabe läuft...",
    "Done - did you hear yourself?": "Fertig - hast du dich gehört?",
    "Test failed: {reason}": "Test fehlgeschlagen: {reason}",
    "Test cancelled.": "Test abgebrochen.",
    "System default": "Systemstandard",
    # Network kinds (voice2fritz.network)
    "Local network": "Lokales Netzwerk",
    "VPN": "VPN",
    "Virtual network": "Virtuelles Netzwerk",
    "Loopback": "Loopback",
    "Unknown": "Unbekannt",
    # Setup wizard (voice2fritz.gui.setup_wizard)
    "Connect": "Verbinden",
    "Enter the username and password of the IP phone you just created.":
        "Gib Benutzername und Kennwort des eben angelegten IP-Telefons ein.",
    "Connecting...": "Verbinde...",
    "Connected as {account}.": "Verbunden als {account}.",
    "The FRITZ!Box rejected the login. Use the username and password of the IP phone, not the FRITZ!Box login.":
        "Die FRITZ!Box hat die Anmeldung abgelehnt. Verwende Benutzername und Kennwort des IP-Telefons, "
        "nicht die Anmeldung an der FRITZ!Box.",
    "Could not connect: {detail}. Check the host, and that this computer is not on the guest WLAN.":
        "Verbindung fehlgeschlagen: {detail}. Prüfe den Host und dass dieser Computer nicht im Gast-WLAN ist.",
    "No answer from {host}. Try 192.168.178.1, and check that this computer is not on the guest WLAN.":
        "Keine Antwort von {host}. Versuche 192.168.178.1 und prüfe, dass dieser Computer nicht im Gast-WLAN ist.",
    "Call audio goes through the VPN; the FRITZ!Box may not reach it. Turn off the VPN and restart voice2fritz.":
        "Der Anrufton läuft über das VPN; die FRITZ!Box erreicht ihn eventuell nicht. "
        "Schalte das VPN aus und starte voice2fritz neu.",
    "voice2fritz setup": "voice2fritz einrichten",
    "Back": "Zurück",
    "Next": "Weiter",
    "Finish": "Fertigstellen",
    "Open FRITZ!Box": "FRITZ!Box öffnen",
    "Welcome": "Willkommen",
    "This wizard connects voice2fritz to your FRITZ!Box as an IP phone, step by step. Before you start, check that:":
        "Dieser Assistent verbindet voice2fritz Schritt für Schritt als IP-Telefon mit deiner FRITZ!Box. "
        "Bevor du anfängst, prüfe:",
    "This computer is on your home network, by cable or WLAN. The guest WLAN will not work.":
        "Dieser Computer ist per Kabel oder WLAN im Heimnetz. Das Gast-WLAN funktioniert nicht.",
    "Any VPN is turned off for now.": "Ein VPN ist vorerst ausgeschaltet.",
    "You know the password for the FRITZ!Box web interface. It is often printed on a sticker on the bottom of the box.":
        "Du kennst das Passwort der FRITZ!Box-Benutzeroberfläche. Es steht oft auf einem Aufkleber unten auf der Box.",
    "Your headset is plugged in.": "Dein Headset ist angeschlossen.",
    "Check your phone number": "Rufnummer prüfen",
    "Your FRITZ!Box needs at least one phone number from your internet provider.":
        "Deine FRITZ!Box braucht mindestens eine Rufnummer von deinem Internetanbieter.",
    "Click <b>Open FRITZ!Box</b> below and log in.": "Unten auf <b>FRITZ!Box öffnen</b> klicken und anmelden.",
    "Go to <b>Telephony → Own Numbers</b>.": "<b>Telefonie → Eigene Rufnummern</b> öffnen.",
    "Check that at least one number has a green dot.": "Prüfen, dass mindestens eine Rufnummer einen grünen Punkt hat.",
    "If the list is empty, your provider has not set up telephony yet. Most providers do this "
    "automatically. If yours does not, use the FRITZ!Box wizard for adding a phone number, with the "
    "details your provider sent you.":
        "Ist die Liste leer, hat dein Anbieter die Telefonie noch nicht eingerichtet. Die meisten Anbieter "
        "erledigen das automatisch. Falls nicht, nutze den Assistenten der FRITZ!Box zum Einrichten einer "
        "Rufnummer, mit den Daten aus den Unterlagen deines Anbieters.",
    "Create an IP phone": "IP-Telefon anlegen",
    "voice2fritz connects to the FRITZ!Box as an IP phone. Create one for it.":
        "voice2fritz meldet sich als IP-Telefon an der FRITZ!Box an. Lege dafür eines an.",
    "In the FRITZ!Box, go to <b>Telephony → Telephony Devices</b>.":
        "In der FRITZ!Box <b>Telefonie → Telefoniegeräte</b> öffnen.",
    "Click <b>Configure New Device</b>.": "<b>Neues Gerät einrichten</b> klicken.",
    "Choose <b>Telephone (with and without answering machine)</b> and click <b>Next</b>.":
        "<b>Telefon (mit und ohne Anrufbeantworter)</b> wählen und <b>Weiter</b> klicken.",
    "Choose <b>LAN/WLAN (IP telephone)</b> and click <b>Next</b>.":
        "<b>LAN/WLAN (IP-Telefon)</b> wählen und <b>Weiter</b> klicken.",
    "Enter a name, for example <b>voice2fritz</b>.": "Einen Namen eingeben, zum Beispiel <b>voice2fritz</b>.",
    "Choose a <b>username</b> and a <b>password</b>, write both down, then click <b>Next</b>.":
        "<b>Benutzername</b> und <b>Kennwort</b> festlegen, beides aufschreiben und dann <b>Weiter</b> klicken.",
    "Choose the <b>outgoing number</b> that people see when you call them.":
        "Die <b>ausgehende Rufnummer</b> wählen, die Angerufene sehen.",
    "Choose which <b>incoming calls</b> should ring in voice2fritz.":
        "Wählen, bei welchen <b>ankommenden Anrufen</b> voice2fritz klingeln soll.",
    "Finish the wizard. You may need to confirm with a button press on the box or on a DECT handset.":
        "Den Assistenten abschließen. Eventuell musst du per Tastendruck an der Box oder an einem "
        "DECT-Mobilteil bestätigen.",
    "The username and password are new credentials only for voice2fritz. "
    "They are not your FRITZ!Box login.":
        "Benutzername und Kennwort sind neue Zugangsdaten nur für voice2fritz. "
        "Sie sind nicht die Anmeldung an der FRITZ!Box.",
    "Audio": "Ton",
    "Choose your headset, then test it.": "Wähle dein Headset und teste es.",
    "Done": "Fertig",
    "voice2fritz is connected. Make a few test calls:": "voice2fritz ist verbunden. Mach ein paar Testanrufe:",
    "<b>Internal:</b> dial the internal number of a DECT handset, for example <b>**610</b>. This costs nothing.":
        "<b>Intern:</b> die interne Rufnummer eines DECT-Mobilteils wählen, zum Beispiel <b>**610</b>. "
        "Das kostet nichts.",
    "<b>External:</b> call your mobile phone and check that both sides hear each other.":
        "<b>Extern:</b> dein Handy anrufen und prüfen, ob beide Seiten sich hören.",
    "<b>Incoming:</b> call your landline from your mobile phone.":
        "<b>Eingehend:</b> vom Handy aus deine Festnetznummer anrufen.",
    'If something does not work, see the <a href="{url}">troubleshooting section of the setup guide</a>.':
        'Falls etwas nicht funktioniert, hilft die <a href="{url}">Fehlersuche in der Einrichtungsanleitung</a>.',
}

_language = DEFAULT_LANGUAGE


def language_from_locale(locale_name: str) -> str:
    """"de_DE" or "de-DE" -> "de"."""
    return locale_name.replace("-", "_").split("_", 1)[0].lower()


def system_language_offer(locale_name: str, configured: str, declined: str | None) -> str | None:
    """The system language to offer at startup, or None if there's nothing to offer.

    Offered only when the program supports it, it isn't the configured language
    already, and the user hasn't turned down this same offer before.
    """
    system_language = language_from_locale(locale_name)
    if system_language not in LANGUAGES or system_language in (configured, declined):
        return None
    return system_language


def set_language(language: str) -> None:
    global _language
    _language = language if language in LANGUAGES else DEFAULT_LANGUAGE


def current_language() -> str:
    return _language


def tr(text: str, **values) -> str:
    template = _GERMAN.get(text, text) if _language == "de" else text
    return template.format(**values) if values else template
