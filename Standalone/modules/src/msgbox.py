import clr
clr.AddReference("System.Windows.Forms")
import System.Windows.Forms as WinForms

window_title = 'pwned'
window_text = "I'm in your computerz"

WinForms.MessageBox.Show(str(window_text), str(window_title))

print 'Popped'