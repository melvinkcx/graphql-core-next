from typing import Any, Dict, List, Union

from graphql import ExecutionContext, GraphQLSchema, DocumentNode, GraphQLFieldResolver, Middleware, \
    GraphQLTypeResolver, GraphQLError, visit, GraphQLObjectType, GraphQLField, GraphQLString, graphql_sync, Visitor, \
    IDLE, BREAK, ValidationContext, TypeInfo
from graphql.language import ast
from graphql.validation.validate import ValidationAbortedError


class DepthAnalysisVisitor(Visitor):
    def __init__(self, context, max_depth=10):
        self.max_depth = max_depth
        self.context = context

    def enter(self, node, key, parent, path, *args):
        if isinstance(node, ast.NameNode):
            depth = path.count("selection_set")
            if depth > self.max_depth:
                self.context.report_error(GraphQLError(f"Reached max depth of {self.max_depth}"))
                return BREAK

        return IDLE


class CustomExecutionContext(ExecutionContext):
    @classmethod
    def build(
        cls,
        schema: GraphQLSchema,
        document: DocumentNode,
        root_value: Any = None,
        context_value: Any = None,
        raw_variable_values: Dict[str, Any] = None,
        operation_name: str = None,
        field_resolver: GraphQLFieldResolver = None,
        type_resolver: GraphQLTypeResolver = None,
        middleware: Middleware = None,
    ) -> Union[List[GraphQLError], "ExecutionContext"]:
        # Build execution context after visiting it
        errors: List[GraphQLError] = []

        def on_error(error: GraphQLError) -> None:
            errors.append(error)
            raise ValidationAbortedError

        context = ValidationContext(schema=schema, ast=document, type_info=TypeInfo(schema), on_error=on_error)
        try:
            visit(document, DepthAnalysisVisitor(context=context, max_depth=1))
        except ValidationAbortedError:
            pass

        if errors:
            return errors

        return super(CustomExecutionContext, cls).build(
            schema,
            document,
            root_value,
            context_value,
            raw_variable_values,
            operation_name,
            field_resolver,
            type_resolver,
            middleware
        )


schema = GraphQLSchema(
    query=GraphQLObjectType(
        name='RootQueryType',
        fields={
            'hello': GraphQLField(
                GraphQLString,
                resolve=lambda obj, info: 'world'),
            'hey': GraphQLField(
                GraphQLString,
                resolve=lambda obj, info: 'yo'),
            'foo': GraphQLField(
                GraphQLObjectType(
                    name='FooObject',
                    fields={
                        'bar': GraphQLField(GraphQLObjectType(
                            name='BarObject',
                            fields={
                                'xxx': GraphQLField(GraphQLString)
                            }
                        ))
                    }
                ),
                resolve=lambda obj, info: {'bar': {'xxx': 'xxxxx'}}
            ),
            'cat': GraphQLField(
                GraphQLObjectType(
                    name='CatObject',
                    fields={
                        'meow': GraphQLField(GraphQLString)
                    },
                ),
                resolve=lambda obj, info: {"meow": "meowwwww"}
            )
        }))

query = '{ cat { meow } foo { bar { xxx } } }'
# query = '{ hello hey }'

print(graphql_sync(schema, query, execution_context_class=CustomExecutionContext))
