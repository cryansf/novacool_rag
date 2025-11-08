/opt/render/project/src/sanity_check.py

🧠 Running it locally (recommended)
If you’ve cloned your Render repo onto your local machine, open a terminal in that same project folder and run:
python sanity_check.py

That will check every dependency before you push to Render.

🧩 Optional: Running in Render shell
If you prefer to test directly inside Render:


Open your Render Shell (from the “Logs & Shell” tab)


Create and run:
nano sanity_check.py

Paste in the code, save (Ctrl+O, Enter, Ctrl+X), then run:
python sanity_check.py



If all packages are installed correctly, you’ll see:
🎉 All dependencies installed and ready for deployment.


Would you like me to also show how to add a Render build hook so this sanity check runs automatically before your app boots? It’s a 1-liner you can add to your render.yaml.
