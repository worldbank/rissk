# MLSS

This package is used to process survey data from **[Survey solutions](https://mysurvey.solutions/en/)** and create a **Unit risk score**. 
It expects a specific structure for the input files.

## Getting Started

These instructions will guide you on how to install and run this package on your local machine.

### Prerequisites

Make sure you have Python 3.8 or higher installed on your machine. You can verify this by running:

```shell
python --version
```
### Setup
1. Clone this repository to your local machine.
```
git clone git@github.com:RowSquared/mlss.git
```
2. Navigate into the project directory.
```
cd mlss
```
3. Create a new virtual environment inside the project directory.
```
python -m venv venv
```
4. Activate the virtual environment. The command to do this will depend on your operating system:
On **Windows**:
```
venv\Scripts\activate
```
On **Unix or MacOS**:
```
source venv/bin/activate
```
5. Install the required dependencies:
```
pip install -r requirements.txt
```
### Running the Package
To run the package, use the following command, replacing **<survey_folder_path>**, **<survey_name>**, and **<result_path>** with your specific paths:
```
python main.py data.externals=<survey_folder_path> surveys=<survey_name> data.results=<result_path>
```

#### Input Data

The package expects two zip files in the <survey_folder_path> directory:

1. <survey_name>_version_Paradata_All.zip
2. <survey_name>_version_Tabular_All.zip
#### Output Data

The results of running the package will be stored in the specified <result_path> directory. if the path is not specified it will be stored in the result folder.
