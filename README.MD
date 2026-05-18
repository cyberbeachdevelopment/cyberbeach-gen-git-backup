# 🌊 cyberbeach x rezosolver
v1.01

[cyberbeach.cc](https://cyberbeach.cc) & [discord.gg/cyberbeach](https://discord.gg/cyberbeach)

## disclaimer

for educational and research purposes only. users are responsible for how they use this.

## preview

[watch preview video](https://videy.co/v/?id=e8thddEX1)

## discord token generator

---

## features

* async architecture for performance
* multi-threaded execution
* multi solver support (primarily rezosolver)
* dynamic header building
* live title updates

---

## setup

### 1. configure `config.json`

edit the `config.json` file and fill in your API keys/settings.

example:

```json
{
    "data": {
        "rezosolver_api_key": "your_rezosolver_api_key",
        "anysolver_api_key": "",
        "razorcap_api_key": ""
    },
    "mail": {
        "api_key": "your_mail_api_key",
        "smtp": {
            "enabled": false,
            "host": "",
            "imap_host": "",
            "imap_port": 993,
            "username": "",
            "password": "",
            "use_ssl": true,
            "mailbox": "INBOX",
            "domain": ""
        }
    },
    "verification": {
        "enabled": true
    },
    "threads": 1,
    "debug": true
}
```

### config explanation

#### `data`

* `rezosolver_api_key` → your rezosolver API key
* `anysolver_api_key` → optional anysolver API key
* `razorcap_api_key` → optional razorcap API key

#### `mail`

* `api_key` → API key for [freecustom.email](https://www.freecustom.email/) or your mail provider

#### `smtp`

optional custom SMTP/IMAP mail setup:

* `enabled` → enable/disable custom SMTP
* `host` → SMTP host
* `imap_host` → IMAP host
* `imap_port` → IMAP port (default: 993)
* `username` → email username
* `password` → email password
* `use_ssl` → use SSL connection
* `mailbox` → mailbox folder
* `domain` → custom mail domain

#### `verification`

* `enabled` → enables Discord email verification flow

#### `threads`

* amount of worker threads used during generation (3 recommended)

---

### 2. configure `proxies.txt`

add proxies to `input/proxies.txt` using this format:

```txt
user:pass@ip:port
```

example:

```txt
john123:password123@127.0.0.1:8000
proxyuser:mypass@192.168.1.10:9000
```

supported proxy types depend on your provider.

---

### 3. configure `input/user/*` (optional)

* "/username.txt" - insert a list of usernames
* "/bio.txt" - insert a list of bios
* "/status.txt" - insert a list of status(es)
* "/pfp/" - insert a list of profile pictures

---

### 4. run the program

start the generator normally after configuring:

```bash
python main.py
```

---

## updates (1.01)

* new customisation (input/user/*)
* debug can now be disabled through config.json
* improved logging

---

## access / services

* mail nodes → [cyberbeach.cc](https://cyberbeach.cc/)
* solver credits → [huzaif.online](https://huzaif.online/)
* proxy plans → [dataimpulse.com](https://dataimpulse.com/)

### mail server nodes

to purchase a dedicated mail server node for unflagged token generation & avoid term waves: (beta)

* [discord.gg/cyberbeach](https://discord.gg/cyberbeach)

* [cyberbeach.cc](https://cyberbeach.cc)

---

### solver credits

to buy solver credits for rezosolver:

* [huzaif.online](https://huzaif.online/)
  (sign up required, crypto accepted)