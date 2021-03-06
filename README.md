An interactive shell around OnePassword CLI written in python3

# Requirements
## System
* [OnePassword CLI](https://support.1password.com/command-line/)
* python >=3

## Python
* cryptography
* dbus-python
* keyring
* Pygments
* SecretStorage

# How to install
`python setup.py install`

If you are in a virtualenv, without system-package access granted,
and because of a mysterious bug (any help welcomed), you have to run also  
`pip install --force -U dbus-python`

This will certainly output an error, but check all goes right runnning 
`python -c "import secretstorage"`.

If this last command run without any errors, you are good to go!

# How to use is
```shell    
$ oppy --help
usage: oppy [-h] [--config CONFIG] [--debug] [--vault VAULT] profile

1password CLI

positional arguments:
  profile          the 1password profile to use

optional arguments:
  -h, --help       show this help message and exit
  --config CONFIG  path to the conf file
  --debug          toggle the debug mode
  --vault VAULT    set the vault
```

The profile came from the configuration file you use. Default is `~/.config/op.py/config.ini`
This file can contains multiple profile, each one defined by a profile name into square brackets.
Here is an example:

```ini
[profile1]
debug=True
domain=domain1
vault=Private

[profile2]
domain=domain1
vault=null
```

On the command line, specify one of the profile you defined in the configuration file.

    $ oppy profile1 

You can also override options

    $ oppy profile2 --debug --vault=Shared


## TODO
* [ ] add update commands
* [ ] add creation commands


## CONTRIBUTIONS
This project is under the MIT licence and I will enjoy any contributions.  
Just fork this project, write some code and do a pull request!
