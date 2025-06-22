# AUTO POST ON FACEBOOK WITH AI CONTENT

This appears to be a web-based dashboard for monitoring and managing an automated posting system. The "SQA" in the name may suggest that this tool is used for Software Quality Assurance testing of an auto-posting feature.

## Description

The SQA Autopost Dashboard provides a web interface to view the schedule and logs of an automated posting application. It seems to be built with a Python backend, likely using a web framework like Flask or Dash, and renders information in an HTML frontend. The Procfile suggests that this application is ready to be deployed on a cloud platform like Heroku.
### Inferred Features
- Post Scheduling: The post_schedule.json file indicates that the application likely allows users to schedule posts.
- Post Logging: The post_log.json file suggests that the application keeps a log of past posts, which can be viewed on the dashboard.
- Web Dashboard: The presence of HTML templates and a Python web application structure points to a dashboard for visualizing the posting schedule and logs.

## Installation

To run this project locally, you will need to have Python installed. Then, you can follow these steps:

1.  Clone the repository:
    ```
     git clone https://github.com/sajimpk/sqa_autopost_dashbord.git
    ```
    ```bash
    cd sqa_autopost_dashbord
    ```
3.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Once the dependencies are installed, you should be able to run the application using the following command:

```python
python app.py
```
This will likely start a local development server. You can then access the dashboard by navigating to the URL provided in the terminal (usually `http://127.0.0.1:5000` or `http://127.0.0.1:8050`).
