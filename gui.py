import urwid

CURSOR = u"\u2588";

class MultiCursorTextEditor:
    def __init__( self, text="", on_keypress=None ):
        self.walker = MultiCursorListWalker();
        self.lines = MultiCursorListBox( self.walker, text, on_keypress );
        self.loop = urwid.MainLoop( self.lines );

    def launch( self ):
        self.loop.run();

    def keypress( self, key ):
        return self.lines.keypress( (), key, True );

    def create_cursor( self, cid ):
        self.walker.set_alt_focus( cid, 0 );

    def delete_cursor( self, cid ):
        self.walker.delete_cursor( cid );

class MultiCursorEdit( urwid.Text ):
    def __init__( self, text="" ):
        self._selectable = True;
        self._command_map = urwid.Edit._command_map;
        self.is_selected = False;
        self.cursors = {};
        self.edit_text = text;

        super().__init__( text );

    def keypress( self, size, key ):
        if key == 'left':
            self.move_cursor_left( 0 );
        elif key == 'right':
            self.move_cursor_right( 0 );
        elif key == 'backspace':
            self.backspace( 0 );
        elif key == 'delete':
            self.delete( 0 );
        elif len( key ) == 1:
            self.insert_text( 0, key );
        else:
            return key;

        return None;

    def _update_visible( self ):
        text = self.edit_text;
        for cid in self.cursors:
            if self.cursors[cid][1]:
                text = "%s%s%s" % (text[:self.cursors[cid][0]], CURSOR, text[self.cursors[cid][0]+1:]);
        self.set_text( text );

    def move_cursor_left( self, cid ):
        self.move_cursor_to( cid, self.cursors[cid][0] - 1 );

    def move_cursor_right( self, cid ):
        self.move_cursor_to( cid, self.cursors[cid][0] + 1 );

    def move_cursor_to( self, cid, pos ):
        if (pos <= len( self.edit_text ) and pos >= 0 and cid in self.cursors and self.cursors[cid][1]):
            self.cursors[cid][0] = pos;
            self._update_visible();

    def delete_cursor( self, cid ):
        if cid in self.cursors:
            del self.cursors[cid];
            self._update_visible();

    def insert_text( self, cid, text ):
        if cid in self.cursors and self.cursors[cid][1]:
            pos = self.cursors[cid][0];
            self.edit_text = self.edit_text[:pos] + text + self.edit_text[pos:];

            for cid in self.cursors:
                if self.cursors[cid][0] >= pos:
                    self.cursors[cid][0] += 1;

            self._update_visible();

    def delete( self, cid ):
        if cid in self.cursors and self.cursors[cid][1]:
            pos = self.cursors[cid][0];
            self.edit_text = self.edit_text[:pos] + self.edit_text[pos+1:];

            for cid in self.cursors:
                if self.cursors[cid][0] > pos:
                    self.cursors[cid][0] -= 1;
            self._update_visible();

    def backspace( self, cid ):
        if cid in self.cursors:
            pos = self.cursors[cid][0];
            if (self.cursors[cid][1] and pos > 0):
                self.edit_text = self.edit_text[:pos-1] + self.edit_text[pos:];

                for cid in self.cursors:
                    if self.cursors[cid][0] >= pos:
                        self.cursors[cid][0] -= 1;

                self._update_visible();
            return pos;
        else:
            return None;

    def get_line_split( self, cid ):
        if cid in self.cursors:
            pos = self.cursors[cid][0];
            return (self.edit_text[:pos], self.edit_text[pos:], [c for c in self.cursors if self.cursors[c][1] and self.cursors[c][0] >= pos]);
        else:
            return None;

    def get_line( self ):
        return (self.edit_text, [cid for cid in self.cursors if self.cursors[cid][1]]);

    def set_line( self, text ):
        self.edit_text = text;
        self._update_visible();

    def select_this( self, cid, pos ):
        if cid in self.cursors:
            self.cursors[cid][1] = True;
        else:
            self.cursors[cid] = [pos, True];
        self.move_cursor_to( cid, pos );

    def deselect_this( self, cid ):
        if cid in self.cursors and self.cursors[cid][1]:
            self.cursors[cid][1] = False;
            self._update_visible();
            return self.cursors[cid][0];
        else:
            return None;

class MultiCursorListWalker( urwid.ListWalker ):
    def __init__( self ):
        self.focus = 0;
        self.cursors = {};
        self.lines = [ MultiCursorEdit( "" ) ];

    def get_focus( self ):
        return self.get_alt_focus( 0 );

    def get_alt_focus( self, cid ):
        return self._get_widget_at( self.cursors[cid] );

    def set_focus( self, focus ):
        self.set_alt_focus( 0, focus, 0 )

    def set_alt_focus( self, cid, focus, pos=None, offset=0 ):
       
        if cid in self.cursors:
           npos = self._get_widget_at( self.cursors[cid] )[0].deselect_this( cid );
           opos = offset + (npos if npos else 0);

        self.cursors[cid] = focus;
        self._get_widget_at( self.cursors[cid] )[0].select_this( cid, opos if pos == None else pos );

        if cid == 0:
            self.focus = focus;
            self._modified();

        return ;

    def delete_cursor( self, cid ):
        for line in self.lines:
            line.delete_cursor( cid );

        del self.cursors[cid];

    def get_next( self, pos ):
        return self._get_widget_at( pos + 1 );

    def get_prev( self, pos ):
        return self._get_widget_at( pos - 1 );

    def split_line( self, line, cid ):
        widget, ignore = self._get_widget_at( line );
        fore, aft, mcurs = widget.get_line_split( cid );

        widget.set_line( fore );
        nwidget = MultiCursorEdit( aft );

        self.lines.insert( line + 1, nwidget );
        self._modified();

        for c in mcurs:
            if c != cid:
                self.set_alt_focus( c, line + 1 );
            else:
                self.set_alt_focus( c, line + 1, 0 );

    def combine_line_with_prev( self, line ):
        if line == 0:
            return 0;

        widget, ignore = self._get_widget_at( line );
        pwidget, ignore = self._get_widget_at( line - 1 );

        ctext, ccurs = widget.get_line();
        ptext, pcurs = pwidget.get_line();

        pwidget.set_line( ptext + ctext );

        for c in ccurs:
            self.set_alt_focus( c, line - 1, len( ptext ) );

        self.lines.remove( widget );
        self._modified();

    def _get_widget_at( self, pos ):
        if (pos < 0):
            return (None, None);

        if (pos < len( self.lines )):
            return (self.lines[pos], pos);

        assert pos == len( self.lines );

        self.lines.append( MultiCursorEdit( "" ) );

        return (self.lines[-1], pos);


class MultiCursorListBox( urwid.ListBox ):
    def __init__( self, walker, text, on_keypress=None ):
        self.on_keypress = on_keypress;
        super().__init__( walker );
        self.body.set_focus( 0 );
        self.set_all_text( text );

    def set_all_text( self, text ):
        pos = 0;
        for line in text.splitlines():
            widget, ignore = self.body._get_widget_at( pos );
            widget.set_line( line );
            pos += 1;

    def alt_cursor_right( self, cid ):
        self.body.get_alt_focus( cid )[0].move_cursor_right( cid );

    def alt_cursor_left( self, cid ):
        self.body.get_alt_focus( cid )[0].move_cursor_left( cid );

    def alt_cursor_down( self, cid ):
        next_edit, focus = self.body.get_next( self.body.get_alt_focus( cid )[1] );
        if (next_edit != None):
            fcurs = self.body.get_alt_focus( cid )[0].deselect_this( cid );
            self.body.set_alt_focus( cid, focus, fcurs );

    def alt_cursor_up( self, cid ):
        prev_edit, focus = self.body.get_prev( self.body.get_alt_focus( cid )[1] );
        if (prev_edit != None):
            fcurs = self.body.get_alt_focus( cid )[0].deselect_this( cid );
            self.body.set_alt_focus( cid, focus, fcurs );

    def keypress( self, size, key, cid=0 ):
        if cid != 0:
            if (key == 'right'):
                self.alt_cursor_right( cid );
                return None;
            elif (key == 'left'):
                self.alt_cursor_left( cid );
                return None;
            elif (key == 'up'):
                self.alt_cursor_up( cid );
                return None;
            elif (key == 'down'):
                self.alt_cursor_down( cid );
                return None;
            elif (key == 'backspace'):
                self.body.get_alt_focus( cid )[0].backspace( cid );
                return None;
            elif (key == 'delete'):
                self.body.get_alt_focus( cid )[0].delete( cid );
                return None;
            elif (key == 'enter'):
                self.body.split_line( self.body.cursors[1], cid );
                return None;
            elif (len(key) == 1):
                self.body.get_alt_focus( cid )[0].insert_text( cid, key );
                return None;
            else:
                return key;
        else:
            if self.on_keypress:
                self.on_keypress( size, key );
            if (key == 'enter'):
                self.body.split_line( self.body.focus, 0 );
            elif key == 'backspace':
                if self.body.get_focus()[0].backspace( 0 ) == 0:
                    self.body.combine_line_with_prev( self.body.focus );
            else:
                return super().keypress( size, key );

