FROM node AS compile-image

RUN npm install -g @angular/cli

WORKDIR /app
ENV PATH /app/node_modules/.bin:$PATH

COPY package.json /app/package.json
RUN npm install

COPY angular.json /app/
COPY browserslist /app/
COPY tsconfig.app.json /app/
COPY tsconfig.json /app/
COPY tsconfig.spec.json /app/
COPY src /app/src

COPY environment.prod.ts /app/src/environments/environment.ts
COPY environment.prod.ts /app/src/environments

RUN ng build --prod


FROM nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=compile-image /app/dist/onliapa /usr/share/nginx/html
