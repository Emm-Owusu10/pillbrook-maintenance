# Common-password list

`common_passwords.txt` is the list the application checks new passwords against (requirement SR2).

| Item | Value |
|---|---|
| Source | SecLists, file `Passwords/Common-Credentials/100k-most-used-passwords-NCSC.txt` |
| Address | https://github.com/danielmiessler/SecLists |
| Origin of the data | Compiled by the UK National Cyber Security Centre from breach data |
| Licence | SecLists is released under the MIT licence |
| Downloaded on | 31 October 2026 |
| SHA-256 | C2E5696882C603B76BB67A47EE970897E5A76FC4C3F5547ABE3D0CA340C576E0  |

To replace the list, save the new file under the same name and update the table above.
The application refuses to check passwords if this file is missing.