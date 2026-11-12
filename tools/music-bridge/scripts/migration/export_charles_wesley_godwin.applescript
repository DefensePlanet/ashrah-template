tell application "Music"
	-- Find Charles Wesley Godwin playlist
	set playlistFound to false
	set targetPlaylist to null

	repeat with p in user playlists
		if name of p is "Charles Wesley Godwin" then
			set targetPlaylist to p
			set playlistFound to true
			exit repeat
		end if
	end repeat

	if not playlistFound then
		display dialog "Charles Wesley Godwin playlist not found!"
		return
	end if

	-- Export tracks
	set trackList to {}
	repeat with t in tracks of targetPlaylist
		set trackInfo to {title:(name of t), artist:(artist of t), album:(album of t)}
		set end of trackList to trackInfo
	end repeat

	-- Create JSON content
	set jsonContent to "[\n"
	repeat with i from 1 to count of trackList
		set trackInfo to item i of trackList
		set jsonContent to jsonContent & "  {\n"
		set jsonContent to jsonContent & "    \"title\": \"" & (title of trackInfo) & "\",\n"
		set jsonContent to jsonContent & "    \"artist\": \"" & (artist of trackInfo) & "\",\n"
		set jsonContent to jsonContent & "    \"album\": \"" & (album of trackInfo) & "\"\n"
		if i < count of trackList then
			set jsonContent to jsonContent & "  },\n"
		else
			set jsonContent to jsonContent & "  }\n"
		end if
	end repeat
	set jsonContent to jsonContent & "]"

	-- Write to Desktop
	set exportFile to (path to desktop as string) & "charles_wesley_godwin_export.json"

	try
		set fileRef to open for access file exportFile with write permission
		set eof of fileRef to 0
		write jsonContent to fileRef
		close access fileRef

		display notification "Exported " & (count of trackList) & " tracks" with title "Charles Wesley Godwin Export"
		return "SUCCESS: Exported " & (count of trackList) & " tracks to Desktop"

	on error
		try
			close access file exportFile
		end try
		display dialog "Failed to write export file"
		return "ERROR: Could not write file"
	end try

end tell