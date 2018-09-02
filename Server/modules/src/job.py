import clr
clr.AddReference("System")
clr.AddReference("System.Threading")
clr.AddReference("System.Windows.Forms")
import System.Random as Random
import System.Windows.Forms as WinForms
from System.Threading import Thread

randint = Random().Next(1000, 10000)
WinForms.MessageBox.Show(str(randint), 'pwned')
#Thread.Sleep(randint)