# Deploy Backend to Heroku

```cmd
cd backend
git init
git add .
git commit -m "Backend API"
heroku create your-backend-name
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-chrome-for-testing
heroku buildpacks:add https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest
heroku buildpacks:add heroku/python
git push heroku main
```

Your backend will be at: `https://your-backend-name.herokuapp.com`
