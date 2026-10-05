FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY src src
RUN mvn -B -q verify

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/pilot-analyzer-0.1.0-SNAPSHOT.jar /app/analyzer.jar
USER 10001:10001
ENTRYPOINT ["java", "-jar", "/app/analyzer.jar"]
