#include "posts.hpp"

#include <userver/formats/json.hpp>
#include <userver/server/http/http_method.hpp>
#include <userver/server/http/http_request.hpp>
#include <userver/server/http/http_status.hpp>
#include <userver/storages/postgres/component.hpp>
#include <userver/storages/postgres/cluster.hpp>

PostsHandler::PostsHandler(
    const userver::components::ComponentConfig& config,
    const userver::components::ComponentContext& context)
    : HttpHandlerBase(config, context),
      pg_cluster_(context.FindComponent<userver::components::Postgres>("postgres-db").GetCluster()) {}

std::string PostsHandler::HandleRequestThrow(
    const userver::server::http::HttpRequest& request,
    userver::server::request::RequestContext&) const {

    auto token = request.GetHeader("Authorization");
    if (token != "Bearer 123") {
        request.SetResponseStatus(userver::server::http::HttpStatus::kUnauthorized);
        return R"({"error":"Unauthorized"})";
    }

    if (request.GetMethod() == userver::server::http::HttpMethod::kPost) {
        auto json = userver::formats::json::FromString(request.RequestBody());

        if (!json.HasMember("user_id") || !json.HasMember("content")) {
            request.SetResponseStatus(userver::server::http::HttpStatus::kBadRequest);
            return R"({"error":"invalid data"})";
        }

        const auto user_id = json["user_id"].As<int>();
        const auto content = json["content"].As<std::string>();

        auto result = pg_cluster_->Execute(
            userver::storages::postgres::ClusterHostType::kMaster,
            "INSERT INTO posts(author_id, content) VALUES($1, $2) RETURNING id",
            user_id,
            content
        );

        const auto post_id = result.AsSingleRow<int>();

        request.SetResponseStatus(userver::server::http::HttpStatus::kCreated);

        userver::formats::json::ValueBuilder res;
        res["id"] = post_id;
        res["user_id"] = user_id;
        res["content"] = content;

        return userver::formats::json::ToString(res.ExtractValue());
    }

    if (request.GetMethod() == userver::server::http::HttpMethod::kGet) {
        const auto user_id_arg = request.GetArg("user_id");

        userver::formats::json::ValueBuilder arr;

        if (!user_id_arg.empty()) {
            const auto user_id = std::stoi(user_id_arg);

            auto result = pg_cluster_->Execute(
                userver::storages::postgres::ClusterHostType::kSlave,
                "SELECT id, author_id, content FROM posts WHERE author_id = $1 ORDER BY created_at DESC",
                user_id
            );

            for (const auto& row : result) {
                userver::formats::json::ValueBuilder item;
                item["id"] = row["id"].As<int>();
                item["user_id"] = row["author_id"].As<int>();
                item["content"] = row["content"].As<std::string>();
                arr.PushBack(item.ExtractValue());
            }
        } else {
            auto result = pg_cluster_->Execute(
                userver::storages::postgres::ClusterHostType::kSlave,
                "SELECT id, author_id, content FROM posts ORDER BY created_at DESC"
            );

            for (const auto& row : result) {
                userver::formats::json::ValueBuilder item;
                item["id"] = row["id"].As<int>();
                item["user_id"] = row["author_id"].As<int>();
                item["content"] = row["content"].As<std::string>();
                arr.PushBack(item.ExtractValue());
            }
        }

        return userver::formats::json::ToString(arr.ExtractValue());
    }

    request.SetResponseStatus(userver::server::http::HttpStatus::kMethodNotAllowed);
    return R"({"error":"Method not allowed"})";
}