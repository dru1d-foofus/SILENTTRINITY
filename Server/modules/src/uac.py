from _winreg import *


def getUACLevel():
    i, consentPromptBehaviorAdmin, enableLUA, promptOnSecureDesktop = 0, None, None, None
    try:
        Registry = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        RawKey = OpenKey(Registry, "SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
    except:
        return "?"
    while True:
        try:
            name, value, type = EnumValue(RawKey, i)
            if name == "ConsentPromptBehaviorAdmin":
                consentPromptBehaviorAdmin = value
            elif name == "EnableLUA":
                enableLUA = value
            elif name == "PromptOnSecureDesktop":
                promptOnSecureDesktop = value
            i += 1
        except WindowsError:
            break

    if consentPromptBehaviorAdmin == 2 and enableLUA == 1 and promptOnSecureDesktop == 1:
        return "3/3"
    elif consentPromptBehaviorAdmin == 5 and enableLUA == 1 and promptOnSecureDesktop == 1:
        return "2/3"
    elif consentPromptBehaviorAdmin == 5 and enableLUA == 1 and promptOnSecureDesktop == 0:
        return "1/3"
    elif enableLUA == 0:
        return "0/3"
    else:
        return "?"
