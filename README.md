# NOVA-AI-Discord
A Simplistic version of NOVA-AI that runs in Discord, powered by Google's Generative AI (Gemini).


## **How to set up an auto-update and reboot service for your Raspberry Pi bot**

### **1. Navigate to your bot directory**

```bash
cd ~/NOVA-AI-Discord
```

#### **2. Create or edit the auto-update script**

```bash
nano auto_update.sh
```

* This script can be found in the repository folder
* Write your script inside (example: pull updates from Git and restart if changes are detected).
* Save and exit (`CTRL+O`, `Enter`, `CTRL+X`).

#### **3. Make the script executable**

```bash
chmod +x auto_update.sh
```

#### **4. Create a systemd service file**

```bash
sudo nano /etc/systemd/system/nova-update-reboot.service
```

* Add your service configuration, this can be found in the `auto_starts` folder

* Save and exit.

#### **5. Reload systemd to recognize the new service**

```bash
sudo systemctl daemon-reload
```

#### **6. Enable the service to start on boot**

```bash
sudo systemctl enable nova-update-reboot
```

#### **7. Start the service immediately**

```bash
sudo systemctl start nova-update-reboot
```

#### **8. Check service status (optional)**

```bash
sudo systemctl status nova-update-reboot
```

* You should see it active/running.
