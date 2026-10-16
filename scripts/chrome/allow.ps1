# Presses Chrome's "Allow remote debugging?" for our own connection, so Keith never has to (his ask, 2026-10-16).
# A real mouse click: UIA Invoke only moves focus. Chrome also ignores clicks right after the prompt appears.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class Mouse {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  public struct POINT { public int X; public int Y; }
}
'@
$A = [System.Windows.Automation.AutomationElement]
$P = [System.Windows.Automation.PropertyCondition]
$allow = New-Object System.Windows.Automation.AndCondition((New-Object $P($A::NameProperty, 'Allow')), (New-Object $P($A::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)))
$chrome = New-Object $P($A::ClassNameProperty, 'Chrome_WidgetWin_1')
function Find-Allow {
  foreach ($w in $A::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $chrome)) {
    $btn = $w.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $allow)
    if ($btn) { return @($w, $btn) }
  }
}
$clicks = 0
for ($i = 0; $i -lt 40; $i++) {
  $found = Find-Allow
  if (-not $found) {
    if ($clicks) { 'clicked Allow'; exit 0 }
    Start-Sleep -Milliseconds 500
    continue
  }
  $w, $btn = $found
  Start-Sleep -Milliseconds 1500
  $r = $btn.Current.BoundingRectangle
  $old = New-Object Mouse+POINT
  [Mouse]::GetCursorPos([ref]$old) | Out-Null
  [Mouse]::SetForegroundWindow([IntPtr]$w.Current.NativeWindowHandle) | Out-Null
  Start-Sleep -Milliseconds 200
  [Mouse]::SetCursorPos([int]($r.X + $r.Width / 2), [int]($r.Y + $r.Height / 2)) | Out-Null
  [Mouse]::mouse_event(2, 0, 0, 0, [IntPtr]::Zero)
  [Mouse]::mouse_event(4, 0, 0, 0, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 200
  [Mouse]::SetCursorPos($old.X, $old.Y) | Out-Null
  $clicks++
  Start-Sleep -Milliseconds 700
}
if ($clicks) { "Allow still showing after $clicks clicks" } else { 'no Allow prompt within 20 s' }
exit 1
