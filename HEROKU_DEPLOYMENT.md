# Heroku Deployment Guide

This guide will walk you through deploying the MakeReady Report Generator to Heroku.

## Prerequisites

1. A [Heroku account](https://signup.heroku.com/) (free tier is sufficient to start)
2. [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installed on your computer
3. [Git](https://git-scm.com/downloads) installed on your computer

## Deployment Steps

### 1. Login to Heroku

Open a terminal/command prompt and log in to your Heroku account:

```bash
heroku login
```

This will open a browser window for you to log in.

### 2. Initialize Git Repository (if not already done)

If your project is not already a Git repository, initialize it:

```bash
git init
git add .
git commit -m "Initial commit for Heroku deployment"
```

### 3. Create a Heroku App

Create a new Heroku app:

```bash
heroku create makeready-report-generator
```

You can replace `makeready-report-generator` with your preferred app name. If you omit the name, Heroku will generate a random name for you.

### 4. Push to Heroku

Deploy your application to Heroku:

```bash
git push heroku main
```

If your main branch is called `master` instead of `main`, use:

```bash
git push heroku master
```

### 5. Check Deployment

Ensure at least one instance of the app is running:

```bash
heroku ps:scale web=1
```

### 6. Open the App

Open your deployed application in a browser:

```bash
heroku open
```

## Troubleshooting

### View Logs

If your application isn't working as expected, check the logs:

```bash
heroku logs --tail
```

### Restart the App

If you need to restart your application:

```bash
heroku restart
```

### Update the App

After making changes to your code, commit them to Git and then push to Heroku again:

```bash
git add .
git commit -m "Update application"
git push heroku main
```

## Important Notes

1. **File Storage**: This application uses temporary file storage. Files are processed in memory and will not persist after the request is completed or if the dyno restarts.

2. **Dyno Sleeping**: On the free tier, your app will "sleep" after 30 minutes of inactivity. The first request after sleeping might take a few seconds to respond.

3. **Resources**: The free tier has limitations on processing power and memory. If you need more resources, consider upgrading to a paid plan.

## Additional Resources

- [Heroku Dev Center](https://devcenter.heroku.com/)
- [Heroku Python Support](https://devcenter.heroku.com/articles/python-support)
- [Heroku CLI Commands](https://devcenter.heroku.com/articles/heroku-cli-commands)
