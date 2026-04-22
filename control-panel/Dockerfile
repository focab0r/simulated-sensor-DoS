FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our config and the dashboard
COPY nginx.conf /etc/nginx/conf.d/sensor-panel.conf
COPY index.html /usr/share/nginx/html/index.html

RUN chmod o+r /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
