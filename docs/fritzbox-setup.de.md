# voice2fritz mit der FRITZ!Box einrichten

*[English version](fritzbox-setup.md)*

Diese Anleitung ist für alle, die an ihrer FRITZ!Box noch nie
Internettelefonie (VoIP) eingerichtet haben. Sie dauert etwa 10 Minuten.

## So funktioniert es

Die FRITZ!Box ist bereits eine kleine Telefonanlage. Deine
Festnetznummer (vom Internetanbieter) ist auf der Box eingerichtet.
DECT-Mobilteile und analoge Telefone sind als „Telefoniegeräte“ an ihr
angemeldet.

voice2fritz wird ein weiteres Gerät dieser Art, ein **IP-Telefon**. Du
legst das Gerät in der FRITZ!Box an und vergibst dabei Benutzername und
Passwort. Diese trägst du dann in voice2fritz ein. SIP-Zugangsdaten vom
Internetanbieter brauchst du dafür **nicht**.

## Bevor du anfängst

- Dein Computer ist per Kabel oder WLAN im **Heimnetz**. Das Gast-WLAN
  funktioniert nicht.
- Falls du ein VPN nutzt (Firmen-VPN, Tailscale, WireGuard, …), schalte es
  vorerst aus. Wenn alles läuft, kannst du es wieder einschalten und
  ausprobieren.
- Du kennst das Passwort der FRITZ!Box-Benutzeroberfläche. Es steht oft
  auf einem Aufkleber unten auf der Box.
- Ein Headset ist angeschlossen.

## Schritt 1: Prüfen, ob die FRITZ!Box eine Rufnummer hat

1. Im Browser <http://fritz.box> öffnen und anmelden.
2. **Telefonie → Eigene Rufnummern** öffnen.
3. Dort sollte mindestens eine Rufnummer mit grünem Punkt stehen.

Ist die Liste leer, hat dein Anbieter die Telefonie noch nicht
eingerichtet. Die meisten Anbieter erledigen das automatisch. Falls nicht,
folge dem Assistenten der FRITZ!Box zum Einrichten einer Rufnummer, mit
den Daten aus den Unterlagen deines Anbieters. Nur hierfür braucht man
Anbieterdaten, und das hat mit voice2fritz nichts zu tun.

## Schritt 2: Ein IP-Telefon für voice2fritz anlegen

1. **Telefonie → Telefoniegeräte** öffnen.
2. **Neues Gerät einrichten** klicken.
3. **Telefon (mit und ohne Anrufbeantworter)** wählen und **Weiter**
   klicken.
4. **LAN/WLAN (IP-Telefon)** wählen und **Weiter** klicken.
5. Einen Namen vergeben, zum Beispiel `voice2fritz`.
6. **Benutzername** und **Kennwort** festlegen:
   - Das sind neue Zugangsdaten nur für dieses Telefon, nicht die
     Anmeldung an der FRITZ!Box.
   - Als Benutzernamen nimmst du, was die Box vorschlägt oder zulässt.
   - Ein starkes Kennwort mit mindestens 8 Zeichen wählen. Beides
     aufschreiben.
   - **Weiter** klicken.
7. **Ausgehende Rufnummer:** auf der Seite **Telefon für ausgehende
   Gespräche einrichten** die Nummer wählen, die Angerufene sehen sollen,
   und **Weiter** klicken.
8. **Ankommende Anrufe:** wählen, auf welche Rufnummern voice2fritz
   klingeln soll (alle oder eine Auswahl).
9. Den Assistenten abschließen. Eventuell musst du die Einrichtung per
   Tastendruck an der Box oder an einem DECT-Mobilteil bestätigen.

Das neue Gerät steht jetzt in der Liste. Es gilt als nicht angemeldet,
bis voice2fritz sich verbindet.

## Schritt 3: Daten in voice2fritz eintragen

1. voice2fritz starten und **Einstellungen** öffnen.
2. Ausfüllen:

   | Feld         | Wert |
   |--------------|------|
   | Host         | `fritz.box` (oder `192.168.178.1`, die Standard-IP-Adresse der FRITZ!Box) |
   | Benutzername | Der Benutzername des IP-Telefons aus Schritt 2 |
   | Passwort     | Das Kennwort des IP-Telefons aus Schritt 2 |

3. **Speichern** klicken. Das Passwort liegt im Schlüsselbund des Systems,
   nicht in einer Klartextdatei.
4. Die Statusanzeige wird grün, sobald voice2fritz angemeldet ist. Im
   Passwortfeld steht dann *„Passwort getestet und funktioniert“*.
5. In der FRITZ!Box unter **Telefoniegeräte** wird der Eintrag für
   voice2fritz jetzt als angemeldet angezeigt.

## Schritt 4: Ton einrichten

1. In den Einstellungen unter **Mikrofon** und **Lautsprecher** das
   Headset wählen.
2. Sprechen und prüfen, ob sich der Balken **Mikrofonpegel** bewegt.
3. **Mikrofon & Lautsprecher testen** klicken. Es nimmt 3 Sekunden auf und
   spielt sie dann ab.

## Schritt 5: Testanruf

- **Intern:** die interne Rufnummer wählen, die die FRITZ!Box für eines
  deiner DECT-Mobilteile anzeigt (zum Beispiel `**610`). Das kostet
  nichts.
- **Extern:** dein Handy anrufen. Prüfen, ob beide Seiten sich hören.
- **Eingehend:** vom Handy aus die Festnetznummer anrufen. voice2fritz
  zeigt das Fenster für eingehende Anrufe.

## Fehlersuche

| Problem | Wahrscheinliche Ursache |
|---|---|
| *„Gespeichertes Passwort wurde abgelehnt“* oder Fehler 401/403 | Benutzername oder Passwort falsch. Die Zugangsdaten des **IP-Telefons** verwenden, nicht die FRITZ!Box-Anmeldung. In den Einstellungen neu eingeben. |
| Statusanzeige bleibt rot, keine Fehlermeldung | Der Host ist nicht erreichbar. `192.168.178.1` statt `fritz.box` versuchen. Prüfen, dass du nicht im Gast-WLAN bist. |
| Angemeldet, aber kein Ton oder Ton nur in eine Richtung | Die Zeile **IP für Anrufton** in den Einstellungen prüfen. Ist sie orange oder zeigt *VPN*, schickt die FRITZ!Box den Ton an eine Adresse, die sie nicht erreicht. VPN ausschalten und voice2fritz neu starten. |
| Ausgehende Anrufe gehen, eingehende klingeln nicht | In den Einstellungen dieses IP-Telefons in der FRITZ!Box **Ankommende Anrufe** prüfen. |
| Angerufene sehen die falsche Nummer | In den Einstellungen des Geräts in der FRITZ!Box die **ausgehende Rufnummer** ändern. |
| Mikrofonpegel bewegt sich nicht | Falsches Mikrofon gewählt oder das Mikrofon ist in den Soundeinstellungen des Desktops stummgeschaltet. |

Die Schritte wurden an einer FRITZ!Box 6591 Cable mit FRITZ!OS 8.25 geprüft.
Menübezeichnungen können je nach FRITZ!OS-Version leicht abweichen.
