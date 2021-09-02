
## manage users

### Prerequisites

``` 
pip3 install paramiko
```

Example:

```
python3 manage_user.py -l hvolos01 -m manifest.xml add_user -u alice -k /Users/hvolos/workspace/keys/alice.pub
```

```
python3 manage_user.py -l hvolos01 -m manifest.xml add_user_to_k8s -u alice
```
