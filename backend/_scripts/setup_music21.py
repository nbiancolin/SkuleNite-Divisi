import os
import music21 as m21

us = m21.environment.UserSettings()
us_path = us.getSettingsPath()
if not os.path.exists(us_path):
    us.create()

#TODO: Fix this so that it uses the musescore headless renderer
us['musescoreDirectPNGPath'] = '/usr/local/bin/musescore'
us['musicxmlPath'] = '/usr/local/bin/musescore'
print('Path to music21 environment', us_path)
print(us)


