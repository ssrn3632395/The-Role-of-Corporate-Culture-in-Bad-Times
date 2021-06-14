
The module reuses some code in _Li, K., Mai, F., Shen, R., & Yan, X. (2021). Measuring corporate culture using machine learning. The Review of Financial Studies. _ [Code Repo](https://github.com/MS20190155/Measuring-Corporate-Culture-Using-Machine-Learning)

The code is tested in Ubuntu 18.04 and macOS Catalina.

## Requirement
- `Python 3.7+`
- Download and uncompress [Stanford CoreNLP v3.9.2](http://nlp.stanford.edu/software/stanford-corenlp-full-2018-10-05.zip). Newer versions may work, but they are not tested. Either [set the environment variable to the location of the uncompressed folder](https://stanfordnlp.github.io/stanfordnlp/corenlp_client.html), or edit the following line in the `global_options.py` to the location of the uncompressed folder, for example:
  > os.environ["CORENLP_HOME"] = "/home/user/stanford-corenlp-full-2018-10-05/"
- Make sure [requirements for CoreNLP](https://stanfordnlp.github.io/CoreNLP/) is met. For example, you need to have Java installed.
