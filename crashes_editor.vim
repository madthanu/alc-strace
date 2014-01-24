set columns=1000
set lines=1000
function! Crashes_editor_vim_version()
	echo 5
endfunction

function! Runprint()
	silent windo! w!
	silent !echo runprint > /tmp/fifo_in
	silent !cat /tmp/fifo_out > /dev/null
	silent windo! e
	wincmd b
	wincmd h
	AnsiEsc
	AnsiEsc
	wincmd b
endfunction

if !exists("g:crashes_editor_started")
	vsp /tmp/current_orderings
	vsp /tmp/replay_output
	wincmd l
	AnsiEsc
	set ro
	set nowrap
	set tabstop=4
	wincmd b
	vertical resize -15
	wincmd t
	wincmd l
	vertical resize +30
	wincmd b
endif

set columns=1000
set lines=1000

let g:crashes_editor_started = 1
set guifont=Monospace\ 12

noremap <F4>		:source /root/application_fs_bugs/strace/crashes_editor.vim<CR>:call Crashes_editor_vim_version()<CR>
vnoremap <F11>		<C-C>:source /root/application_fs_bugs/strace/crashes_editor.vim<CR><C-C>:call Crashes_editor_vim_version()<CR>
inoremap <F11>		<C-O>:source /root/application_fs_bugs/strace/crashes_editor.vim<CR><C-O>:call Crashes_editor_vim_version()<CR>

noremap <F5>		:call Runprint()<CR>
vnoremap <F5>		<C-C>:call Runprint()<CR>
inoremap <F5>		<C-O>:call Runprint()<CR>
