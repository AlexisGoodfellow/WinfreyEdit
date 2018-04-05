import urwid

CURSOR = u"\u2588";

class MultiCursorGui:

    def __init__( self, lines=[], on_key=None, on_cursor=None, on_interrupt=None ):
        """ Create a new MultiCursorGui
        
        Args:
            lines (str array): Initial list of line contents. Must not contain newlines.
            on_key (function): Callback for when user presses a character key. Format is:
                on_key( key )
                    key (str): Single character representing character key
            on_cursor (function): Callback for when user performs navigation. Format is:
                on_cursor( mvmt )
                    mvmt (str): String representing cursor movement. Valid values are:
                                'left', 'right', 'up', 'down', 'backspace', 'delete', 'enter'
        """
        self.started = False;
        self.walker = MultiCursorListWalker();
        self.lines = MultiCursorListBox( self.walker, lines, on_key, on_cursor, on_interrupt );
        self.loop = urwid.MainLoop( self.lines );

    def launch( self ):
        self.started = True;
        self.loop.run();

    def change_line( self, line, text, cursors ):
        """ Sets text and cursor positions for a single line.

            Args:
                line (int): Index of line to be changed (from 0)
                text (str): Text to overwrite line with
                cursors (int array): List of cursor positions within the line
        """
        loop = self.loop if self.started else None
        self.walker.change_line( line, text, cursors, loop );

    def add_line( self, prev_pos, text, cursors ):
        """ Adds a line beneath the given position.

            Args:
                prev_pos (int): Index of line which will come immediately before the new line
                text (str): Text for the new line to inherit
                cursors (int array): List of cursor positions within the new line
        """
        self.walker.add_line( prev_pos, text, cursors );

    def delete_line( self, line ):
        """ Deletes the given line.
            
            Args:
                line (int): Index of line to be deleted
        """
        self.walker.delete_line( line );

class MultiCursorText( urwid.Text ):
    def __init__( self, text="" ):
        self._selectable = True;
        self._command_map = urwid.Edit._command_map;
        self.is_selected = False;
        super().__init__( text );

    def keypress( self, size, key ):
        return key;

    def set_line( self, text, cursors=[] ):
        for cursor in cursors:
            text = "%s%s%s" % (text[:cursor], CURSOR, text[cursor+1:]);
        self.set_text( text );

class MultiCursorListWalker( urwid.ListWalker ):
    def __init__( self ):
        self.focus = 0;
        self.lines = [];

    def get_focus( self ):
        return self._get_widget_at( self.focus );

    def set_focus( self, focus ):
        if focus < len( self.lines ):
            self.focus = focus;
            self._modified();
        else:
            raise IndexError;

    def get_next( self, pos ):
        return self._get_widget_at( pos + 1 );

    def get_prev( self, pos ):
        return self._get_widget_at( pos - 1 );

    def add_line( self, prev_pos, text, cursors ):
        nwidget = MultiCursorText();
        self.lines.insert( prev_pos + 1, nwidget );
        nwidget.set_line( text, cursors );

    def delete_line( self, pos ):
        widget, ignore = self._get_widget_at( pos );
        self.lines.remove( widget );

    def change_line( self, pos, text, cursors, loop ):
        widget, ignore = self._get_widget_at( pos );
        widget.set_line( text, cursors );
        if loop:
            loop.draw_screen()
        self._modified()

    def _get_widget_at( self, pos ):
        if pos < 0 or pos >= len( self.lines ):
            return (None, None);
        else:
            return (self.lines[pos], pos);

class MultiCursorListBox( urwid.ListBox ):
    def __init__( self, walker, lines, on_key=None, on_cursor=None, on_interrupt=None ):
        self.on_key = on_key;
        self.on_cursor = on_cursor;
        self.on_interrupt = on_interrupt;
        super().__init__( walker );
        self.set_all_lines( lines );

    def set_all_lines( self, lines ):
        pos = 0;
        for line in lines:
            self.body.add_line( pos - 1, line, [0] if pos == 0 else [] );
            pos += 1;

    def keypress( self, size, key ):
        if (key == 'right'):
            self.on_cursor( 'right' );
            return None;
        elif (key == 'left'):
            self.on_cursor( 'left' );
            return None;
        elif (key == 'up'):
            self.on_cursor('up');
            return super().keypress( size, key );
        elif (key == 'down'):
            self.on_cursor('down');
            return super().keypress( size, key );
        elif (key == 'backspace'):
            self.on_cursor('backspace');
            return None;
        elif (key == 'delete'):
            self.on_cursor('delete');
            return None;
        elif (key == 'enter'):
            self.on_cursor('enter');
            return None;
        elif (key == 'esc'):
            self.on_interrupt();
            raise urwid.ExitMainLoop;
        elif len(key) == 1:
            self.on_key( key );
            return None;
        else:
            return key;


