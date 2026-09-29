FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /src
COPY . .
ARG MODULE
RUN mvn -B -q -pl "${MODULE}" -am -DskipTests package \
    && cp "/src/${MODULE}/target/${MODULE}-0.1.0-SNAPSHOT.jar" /tmp/app.jar

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /tmp/app.jar /app/app.jar
USER 10001:10001
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
