from code import InteractiveConsole

try:
    import readline
except ImportError:
    print("Module readline not available.")
else:
    import rlcompleter

    readline.parse_and_bind("tab: complete")
console = InteractiveConsole(locals={**globals(), **locals()})
console.interact()
