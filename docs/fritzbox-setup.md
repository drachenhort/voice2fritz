# Setting up voice2fritz with your FRITZ!Box

*[Deutsche Version](fritzbox-setup.de.md)*

This guide is for people who have never set up internet telephony (VoIP)
on their FRITZ!Box. It takes about 10 minutes.

## How it works

Your FRITZ!Box already acts as a small telephone exchange. Your landline
number (from your internet provider) lives on the box. Your DECT handsets
and analog phones are attached to it as "telephony devices".

voice2fritz becomes one more device of this kind, an **IP phone**. You
create the device on the FRITZ!Box, which gives you a username and
password. You then enter them in voice2fritz. You do **not** need any SIP
details from your internet provider.

## Before you start

- Your computer is on your **home network**, by cable or WLAN. The guest
  WLAN will not work.
- If you use a VPN (company VPN, Tailscale, WireGuard, …), turn it off for
  now. Once everything works, you can try with it on.
- You know the password for the FRITZ!Box web interface. It is often
  printed on a sticker on the bottom of the box.
- A headset is plugged in.

## Step 1: Check that the FRITZ!Box has a phone number

1. Open <http://fritz.box> in your browser and log in.
2. Go to **Telephony → Own Numbers**.
3. You should see at least one number with a green dot.

If the list is empty, your provider has not set up telephony yet. Most
providers do this automatically. If yours does not, follow the FRITZ!Box
wizard for adding a phone number, using the details your provider sent
you. This is the only time provider details are needed, and it is not
specific to voice2fritz.

## Step 2: Create an IP phone for voice2fritz

1. Go to **Telephony → Telephony Devices**.
2. Click **Configure New Device**.
3. Choose **Telephone (with and without answering machine)** and click
   **Next**.
4. Choose **LAN/WLAN (IP telephone)** and click **Next**.
5. Give it a name, for example `voice2fritz`.
6. Enter a **username** and a **password**:
   - These are new credentials only for this phone. They are not your
     FRITZ!Box login.
   - Use whatever username the box suggests or allows.
   - Use a strong password with at least 8 characters. Write down both.
   - Click **Next**.
7. **Outgoing number:** on the next page (for outgoing calls), choose the
   number that people should see when you call them, then click **Next**.
8. **Incoming calls:** choose which numbers should ring in voice2fritz
   (all numbers or a selection).
9. Finish the wizard. You may need to confirm with a button press on the
   box or on a DECT handset.

The new device now appears in the list. It shows as not registered until
voice2fritz connects.

## Step 3: Enter the details in voice2fritz

1. Start voice2fritz and open **Settings**.
2. Fill in:

   | Field    | Value |
   |----------|-------|
   | Host     | `fritz.box` (or `192.168.178.1`, the FRITZ!Box's default IP address) |
   | Username | The IP phone username from Step 2 |
   | Password | The IP phone password from Step 2 |

3. Click **Save**. The password is stored in your system keyring, not in a
   plain file.
4. The status light turns green when voice2fritz is registered. The
   password field then says *"Password tested and working"*.
5. In the FRITZ!Box under **Telephony Devices**, the voice2fritz entry now
   shows as registered.

## Step 4: Set up audio

1. In Settings, choose your headset under **Mic** and **Speaker**.
2. Speak and watch the **Mic level** bar move.
3. Click **Test mic & speaker**. It records 3 seconds and plays them back.

## Step 5: Make a test call

- **Internal:** dial the internal number the FRITZ!Box shows for one of
  your DECT handsets (for example `**610`) to ring it. This costs nothing.
- **External:** call your mobile phone. Check that both sides can hear
  each other.
- **Incoming:** call your landline from your mobile. voice2fritz shows the
  incoming-call popup.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| *"Saved password was rejected"* or a 401/403 error | Wrong username or password. Use the **IP phone** credentials, not the FRITZ!Box login. Retype them in Settings. |
| Status light stays red, no error | The host cannot be reached. Try `192.168.178.1` instead of `fritz.box`. Check that you are not on the guest WLAN. |
| Registered, but no sound or one-way sound | Check the **Call audio IP** row in Settings. If it is orange or shows *VPN*, the FRITZ!Box is sending audio to an address it cannot reach. Turn off the VPN and restart voice2fritz. |
| Outgoing calls work but incoming calls do not ring | In the FRITZ!Box device settings for this IP phone, check **Incoming calls**. |
| Callers see the wrong number | Change **Outgoing number** in the FRITZ!Box device settings. |
| Mic level bar does not move | Wrong mic chosen, or the mic is muted in your desktop's sound settings. |

Menu names can differ slightly between FRITZ!OS versions.
